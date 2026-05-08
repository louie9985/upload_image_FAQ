from __future__ import annotations

import threading

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.db.models import QuerySet
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.services import log_action
from faq.models import BatchJob, FaqDraft, GenerationItem, LlmUsageLog, UploadedImage, UploadRecord
from faq.serializers import (
    BatchJobSerializer,
    FaqDraftSerializer,
    GenerationItemBulkSerializer,
    GenerationItemSerializer,
    ImageUploadSerializer,
    LlmUsageLogSerializer,
    UploadedImageSerializer,
    UploadRecordSerializer,
    WebhookUploadSerializer,
)
from faq.tasks import generate_batch_faqs, upload_batch_to_webhook


class OwnerQuerysetMixin:
    def for_user(self, queryset: QuerySet):
        user = self.request.user
        if user.is_staff:
            return queryset
        if hasattr(queryset.model, "owner"):
            return queryset.filter(owner=user)
        if hasattr(queryset.model, "batch"):
            return queryset.filter(batch__owner=user)
        return queryset


class BatchJobViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = BatchJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.for_user(BatchJob.objects.select_related("owner").prefetch_related("images", "drafts", "generation_items"))

    def perform_create(self, serializer):
        batch = serializer.save(owner=self.request.user)
        log_action(self.request.user, "create_batch", "BatchJob", batch.pk, request=self.request)

    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser], url_path="images")
    def upload_images(self, request, pk=None):
        batch = self.get_object()
        serializer = ImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        start_order = batch.images.count()
        created = []
        for index, file in enumerate(serializer.validated_data["files"], start=start_order):
            created.append(
                UploadedImage.objects.create(
                    batch=batch,
                    image=file,
                    original_name=file.name,
                    sort_order=index,
                )
            )
        batch.total_count = batch.images.count()
        batch.save(update_fields=["total_count", "updated_at"])
        log_action(request.user, "upload_images", "BatchJob", batch.pk, request=request, summary={"count": len(created)})
        return Response(UploadedImageSerializer(created, many=True, context={"request": request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="generate")
    def generate(self, request, pk=None):
        batch = self.get_object()
        if not batch.generation_items.exists() and not batch.images.exists():
            return Response({"detail": "请先上传图片。"}, status=status.HTTP_400_BAD_REQUEST)
        run_task(generate_batch_faqs, batch.pk)
        log_action(request.user, "start_generate", "BatchJob", batch.pk, request=request)
        return Response({"ok": True, "batch_id": batch.pk})

    @action(detail=True, methods=["put"], url_path="generation-items")
    def generation_items(self, request, pk=None):
        batch = self.get_object()
        serializer = GenerationItemBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        image_map = {image.pk: image for image in batch.images.all()}
        requested_ids = {image_id for item in serializer.validated_data["items"] for image_id in item["image_ids"]}
        invalid_ids = requested_ids - set(image_map)
        if invalid_ids:
            return Response({"detail": f"图片不存在或不属于当前任务：{sorted(invalid_ids)}"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            batch.drafts.all().delete()
            batch.generation_items.all().delete()
            created = []
            for item in serializer.validated_data["items"]:
                generation_item = GenerationItem.objects.create(
                    batch=batch,
                    title=item["title"],
                    description=item["description"],
                    sort_order=item["sort_order"],
                    is_combined=item["is_combined"],
                )
                generation_item.images.set([image_map[image_id] for image_id in item["image_ids"]])
                created.append(generation_item)
        log_action(request.user, "save_generation_items", "BatchJob", batch.pk, request=request, summary={"count": len(created)})
        return Response(GenerationItemSerializer(created, many=True, context={"request": request}).data)

    @action(detail=True, methods=["get"], url_path="progress")
    def progress(self, request, pk=None):
        batch = self.get_object()
        percent = 0
        if batch.total_count:
            percent = int(batch.processed_count / batch.total_count * 100)
        return Response(
            {
                "id": batch.pk,
                "status": batch.status,
                "total_count": batch.total_count,
                "processed_count": batch.processed_count,
                "failed_count": batch.failed_count,
                "current_step": batch.current_step,
                "error_message": batch.error_message,
                "percent": percent,
            }
        )

    @action(detail=True, methods=["get"], url_path="drafts")
    def drafts(self, request, pk=None):
        batch = self.get_object()
        queryset = batch.drafts.select_related("image", "generation_item").prefetch_related("generation_item__images").all()
        return Response(FaqDraftSerializer(queryset, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="upload-webhook")
    def upload_webhook(self, request, pk=None):
        batch = self.get_object()
        serializer = WebhookUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save_config(request.user)
        if not batch.drafts.filter(status=FaqDraft.Status.GENERATED).exists():
            return Response({"detail": "没有可上传的已生成问答。"}, status=status.HTTP_400_BAD_REQUEST)
        upload_items = serializer.validated_data.get("upload_items")
        if upload_items:
            generated_ids = set(batch.drafts.filter(status=FaqDraft.Status.GENERATED).values_list("id", flat=True))
            requested_ids = {draft_id for item in upload_items for draft_id in item["draft_ids"]}
            invalid_ids = requested_ids - generated_ids
            if invalid_ids:
                return Response({"detail": f"草稿不可上传或不存在：{sorted(invalid_ids)}"}, status=status.HTTP_400_BAD_REQUEST)
        run_task(upload_batch_to_webhook, batch.pk, serializer.validated_data["webhook_url"], request.user.pk, upload_items)
        log_action(request.user, "start_webhook_upload", "BatchJob", batch.pk, request=request)
        return Response({"ok": True, "batch_id": batch.pk})


class UploadedImageViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = UploadedImageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.for_user(UploadedImage.objects.select_related("batch"))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["require_description"] = self.action in {"partial_update", "update"}
        return context

    def perform_update(self, serializer):
        image = serializer.save()
        log_action(self.request.user, "update_image_description", "UploadedImage", image.pk, request=self.request)


class FaqDraftViewSet(OwnerQuerysetMixin, viewsets.ModelViewSet):
    serializer_class = FaqDraftSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.for_user(FaqDraft.objects.select_related("batch", "image", "generation_item").prefetch_related("generation_item__images"))

    def perform_update(self, serializer):
        draft = serializer.save()
        log_action(self.request.user, "update_faq_draft", "FaqDraft", draft.pk, request=self.request)


class UploadRecordViewSet(OwnerQuerysetMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = UploadRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.for_user(UploadRecord.objects.select_related("batch", "draft", "uploader"))


class LlmUsageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        queryset = LlmUsageLog.objects.select_related("batch", "draft").filter(batch__owner=request.user)
        totals = queryset.aggregate(
            prompt_tokens=Sum("prompt_tokens"),
            completion_tokens=Sum("completion_tokens"),
            total_tokens=Sum("total_tokens"),
        )
        recent = queryset.order_by("-created_at")[:20]
        return Response(
            {
                "prompt_tokens": totals["prompt_tokens"] or 0,
                "completion_tokens": totals["completion_tokens"] or 0,
                "total_tokens": totals["total_tokens"] or 0,
                "items": LlmUsageLogSerializer(recent, many=True).data,
            }
        )


def run_task(task, *args):
    if settings.CELERY_TASK_ALWAYS_EAGER:
        threading.Thread(target=task.run, args=args, daemon=True).start()
        return
    task.delay(*args)

