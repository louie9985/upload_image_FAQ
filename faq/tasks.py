from __future__ import annotations

from pathlib import Path
from typing import Any

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from audit.services import log_action
from faq.models import BatchJob, FaqDraft, GenerationItem, LlmUsageLog, UploadRecord, UploadedImage
from integrations.llm_client import LLMClient
from integrations.webhook_client import WebhookClient


@shared_task
def generate_batch_faqs(batch_id: int) -> None:
    batch = BatchJob.objects.select_related("owner").get(pk=batch_id)
    items = list(batch.generation_items.prefetch_related("images").all())
    if not items:
        items = _create_default_generation_items(batch)
    batch.status = BatchJob.Status.GENERATING
    batch.total_count = len(items)
    batch.processed_count = 0
    batch.failed_count = 0
    batch.current_step = "开始生成问答"
    batch.error_message = ""
    batch.save(update_fields=["status", "total_count", "processed_count", "failed_count", "current_step", "error_message", "updated_at"])

    client = LLMClient()
    last_error = ""
    for item in items:
        images = list(item.images.all())
        first_image = images[0] if images else None
        image_names = "、".join(image.original_name for image in images)
        draft, _ = FaqDraft.objects.get_or_create(batch=batch, generation_item=item, defaults={"image": first_image})
        try:
            if not item.description.strip():
                raise ValueError("生成项描述不能为空。")
            batch.current_step = f"正在生成：{item.title}"
            batch.save(update_fields=["current_step", "updated_at"])
            generated = client.generate(description=item.description, image_name=image_names or item.title)
            draft.image = first_image
            draft.question = generated.question
            draft.similar_questions = generated.similar_questions
            draft.answer_text = generated.answer_text
            draft.status = FaqDraft.Status.GENERATED
            draft.error_message = ""
            draft.save()
            LlmUsageLog.objects.create(
                batch=batch,
                draft=draft,
                model=generated.model,
                prompt_tokens=generated.prompt_tokens,
                completion_tokens=generated.completion_tokens,
                total_tokens=generated.total_tokens,
                usage_detail=generated.usage_detail or {},
                ok=True,
            )
        except Exception as exc:  # noqa: BLE001 - task status needs the user-facing message.
            last_error = str(exc)
            draft.status = FaqDraft.Status.FAILED
            draft.error_message = last_error
            draft.save(update_fields=["status", "error_message", "updated_at"])
            LlmUsageLog.objects.create(batch=batch, draft=draft, model=settings.LLM_MODEL, ok=False, error_message=last_error)
            batch.failed_count += 1
        finally:
            batch.processed_count += 1
            batch.save(update_fields=["processed_count", "failed_count", "updated_at"])

    batch.status = BatchJob.Status.GENERATED if batch.failed_count == 0 else BatchJob.Status.FAILED
    batch.current_step = "问答生成完成" if batch.failed_count == 0 else "问答生成失败"
    batch.error_message = "" if batch.failed_count == 0 else last_error or f"{batch.failed_count} 条问答生成失败。"
    batch.save(update_fields=["status", "current_step", "error_message", "updated_at"])
    log_action(batch.owner, "generate_batch_finished", "BatchJob", batch.pk, summary={"failed_count": batch.failed_count})


@shared_task
def upload_batch_to_webhook(batch_id: int, webhook_url: str, user_id: int | None = None, upload_items: list[dict[str, Any]] | None = None) -> None:
    batch = BatchJob.objects.select_related("owner").get(pk=batch_id)
    draft_map = {
        draft.pk: draft
        for draft in batch.drafts.select_related("image", "generation_item").prefetch_related("generation_item__images").filter(status=FaqDraft.Status.GENERATED)
    }
    items = _build_upload_items(draft_map, upload_items)
    batch.status = BatchJob.Status.UPLOADING
    batch.total_count = len(items)
    batch.processed_count = 0
    batch.failed_count = 0
    batch.current_step = "开始上传 webhook"
    batch.error_message = ""
    batch.save(update_fields=["status", "total_count", "processed_count", "failed_count", "current_step", "error_message", "updated_at"])

    client = WebhookClient()
    uploader = batch.owner if user_id is None else batch.owner.__class__.objects.filter(pk=user_id).first()
    last_error = ""
    for item in items:
        drafts = item["drafts"]
        first_draft = drafts[0]
        upload_images = _collect_draft_images(drafts)
        image_paths = [Path(settings.MEDIA_ROOT) / image.image.name for image in upload_images]
        source_draft_ids = [draft.pk for draft in drafts]
        try:
            image_names = "、".join(image.original_name for image in upload_images)
            batch.current_step = f"正在上传：{image_names}"
            batch.save(update_fields=["current_step", "updated_at"])
            result = client.upload_one(
                webhook_url=webhook_url,
                question=item["question"],
                similar_questions=item["similar_questions"],
                answer_text=item["answer_text"],
                image_paths=image_paths,
            )
            UploadRecord.objects.create(
                batch=batch,
                draft=first_draft,
                uploader=uploader,
                question=item["question"],
                similar_questions=item["similar_questions"],
                answer_text=item["answer_text"],
                image_cdn_urls=result.cdn_urls or [],
                wechat_image_items=result.image_items or [],
                wechat_record_id=result.record_id,
                wechat_record_values=result.record_values or {},
                source_draft_ids=source_draft_ids,
                ok=result.ok,
                response_summary=result.response or {},
            )
            if not result.ok:
                batch.failed_count += 1
                last_error = "Webhook 返回失败。"
        except Exception as exc:  # noqa: BLE001 - persist failure record for users.
            last_error = str(exc)
            batch.failed_count += 1
            UploadRecord.objects.create(
                batch=batch,
                draft=first_draft,
                uploader=uploader,
                question=item["question"],
                similar_questions=item["similar_questions"],
                answer_text=item["answer_text"],
                ok=False,
                wechat_image_items=[],
                wechat_record_values={},
                source_draft_ids=source_draft_ids,
                response_summary={"error": str(exc)},
            )
        finally:
            batch.processed_count += 1
            batch.save(update_fields=["processed_count", "failed_count", "updated_at"])

    batch.status = BatchJob.Status.COMPLETED if batch.failed_count == 0 else BatchJob.Status.FAILED
    batch.current_step = "Webhook 上传完成" if batch.failed_count == 0 else "Webhook 上传失败"
    batch.error_message = "" if batch.failed_count == 0 else last_error or f"{batch.failed_count} 条记录上传失败。"
    batch.save(update_fields=["status", "current_step", "error_message", "updated_at"])
    log_action(batch.owner, "upload_batch_finished", "BatchJob", batch.pk, summary={"failed_count": batch.failed_count})


def _build_upload_items(draft_map: dict[int, FaqDraft], upload_items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if upload_items:
        items = []
        for upload_item in upload_items:
            drafts = [draft_map[draft_id] for draft_id in upload_item["draft_ids"] if draft_id in draft_map]
            if not drafts:
                continue
            items.append(
                {
                    "drafts": drafts,
                    "question": str(upload_item["question"]).strip(),
                    "similar_questions": [str(item).strip() for item in upload_item["similar_questions"] if str(item).strip()],
                    "answer_text": str(upload_item["answer_text"]).strip(),
                }
            )
        return items

    return [
        {
            "drafts": [draft],
            "question": draft.question,
            "similar_questions": draft.similar_questions,
            "answer_text": draft.answer_text,
        }
        for draft in draft_map.values()
    ]


def _create_default_generation_items(batch: BatchJob) -> list[GenerationItem]:
    items = []
    for index, image in enumerate(batch.images.all(), start=1):
        item = GenerationItem.objects.create(
            batch=batch,
            title=str(index),
            description=image.description,
            sort_order=index - 1,
            is_combined=False,
        )
        item.images.set([image])
        items.append(item)
    return items


def _collect_draft_images(drafts: list[FaqDraft]):
    images = []
    seen_ids = set()
    for draft in drafts:
        if draft.generation_item_id:
            draft_images = list(draft.generation_item.images.all())
        else:
            draft_images = [draft.image] if draft.image else []
        for image in draft_images:
            if image.pk in seen_ids:
                continue
            seen_ids.add(image.pk)
            images.append(image)
    return images


@shared_task
def cleanup_old_media_images(days: int = 7) -> dict[str, int]:
    """
    清理本地 media 中 7 天前的 UploadedImage 文件与记录。

    - 仅影响本地 MEDIA_ROOT 下的图片文件（ImageField storage）。
    - 以 UploadedImage.created_at 作为过期判断。
    """

    cutoff = timezone.now() - timezone.timedelta(days=days)
    qs = UploadedImage.objects.filter(created_at__lt=cutoff).only("id", "image")

    deleted_files = 0
    deleted_rows = 0
    failed = 0

    for image in qs.iterator(chunk_size=500):
        try:
            with transaction.atomic():
                # 先删文件（storage），再删记录，避免残留磁盘文件。
                if image.image and image.image.name:
                    image.image.delete(save=False)
                    deleted_files += 1
                image.delete()
                deleted_rows += 1
        except Exception:  # noqa: BLE001 - periodic cleanup should not abort the whole run.
            failed += 1

    return {"deleted_files": deleted_files, "deleted_rows": deleted_rows, "failed": failed}

