from __future__ import annotations

from rest_framework import serializers

from faq.models import BatchJob, FaqDraft, GenerationItem, LlmUsageLog, UploadedImage, UploadRecord, WebhookConfig
from integrations.image_utils import is_allowed_image


class BatchJobSerializer(serializers.ModelSerializer):
    image_count = serializers.IntegerField(source="images.count", read_only=True)

    class Meta:
        model = BatchJob
        fields = [
            "id",
            "title",
            "status",
            "total_count",
            "processed_count",
            "failed_count",
            "current_step",
            "error_message",
            "image_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["status", "total_count", "processed_count", "failed_count", "current_step", "error_message"]


class UploadedImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = UploadedImage
        fields = ["id", "batch", "image", "image_url", "original_name", "description", "sort_order", "created_at"]
        read_only_fields = ["batch", "original_name", "sort_order", "created_at"]

    def get_image_url(self, obj: UploadedImage) -> str:
        request = self.context.get("request")
        url = obj.image.url if obj.image else ""
        return request.build_absolute_uri(url) if request and url else url

    def validate_description(self, value: str) -> str:
        if self.context.get("require_description") and not value.strip():
            raise serializers.ValidationError("图片描述为必填项。")
        return value.strip()


class ImageUploadSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.ImageField(), allow_empty=False)

    def validate_files(self, files):
        for file in files:
            if not is_allowed_image(file.name):
                raise serializers.ValidationError("仅支持 png、jpg、jpeg 图片。")
        return files


class FaqDraftSerializer(serializers.ModelSerializer):
    image = UploadedImageSerializer(read_only=True)
    generation_item = serializers.PrimaryKeyRelatedField(read_only=True)
    generation_title = serializers.CharField(source="generation_item.title", read_only=True)
    generation_image_urls = serializers.SerializerMethodField()

    class Meta:
        model = FaqDraft
        fields = [
            "id",
            "batch",
            "image",
            "generation_item",
            "generation_title",
            "generation_image_urls",
            "question",
            "similar_questions",
            "answer_text",
            "status",
            "error_message",
            "is_edited",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["batch", "image", "status", "error_message", "created_at", "updated_at"]

    def get_generation_image_urls(self, obj: FaqDraft) -> list[str]:
        request = self.context.get("request")
        if not obj.generation_item_id:
            if obj.image and obj.image.image:
                url = obj.image.image.url
                return [request.build_absolute_uri(url) if request else url]
            return []
        urls = []
        for image in obj.generation_item.images.all():
            if not image.image:
                continue
            url = image.image.url
            urls.append(request.build_absolute_uri(url) if request else url)
        return urls

    def validate_question(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("问题不能为空。")
        return value.strip()

    def validate_answer_text(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("答案不能为空。")
        return value.strip()

    def validate_similar_questions(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("相似问题不能为空。")
        return [str(item).strip() for item in value if str(item).strip()]

    def update(self, instance: FaqDraft, validated_data):
        instance.is_edited = True
        return super().update(instance, validated_data)


class WebhookUploadItemSerializer(serializers.Serializer):
    draft_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    question = serializers.CharField(max_length=200)
    similar_questions = serializers.ListField(child=serializers.CharField(max_length=200), allow_empty=False)
    answer_text = serializers.CharField()

    def validate_draft_ids(self, value: list[int]) -> list[int]:
        unique_ids = list(dict.fromkeys(value))
        if len(unique_ids) > 5:
            raise serializers.ValidationError("单条 webhook 记录最多合并 5 张图片。")
        return unique_ids

    def validate_answer_text(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("答案不能为空。")
        return value

    def validate_question(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("问题不能为空。")
        return value

    def validate_similar_questions(self, value: list[str]) -> list[str]:
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        if not cleaned:
            raise serializers.ValidationError("相似问题不能为空。")
        return cleaned


class WebhookUploadSerializer(serializers.Serializer):
    webhook_url = serializers.URLField()
    upload_items = WebhookUploadItemSerializer(many=True, required=False)

    def save_config(self, user):
        return WebhookConfig.objects.update_or_create(owner=user, defaults={"webhook_url": self.validated_data["webhook_url"]})


class GenerationItemInputSerializer(serializers.Serializer):
    image_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    title = serializers.CharField(max_length=128)
    description = serializers.CharField()
    sort_order = serializers.IntegerField(min_value=0)
    is_combined = serializers.BooleanField(default=False)

    def validate_description(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("生成项描述不能为空。")
        return value

    def validate_image_ids(self, value: list[int]) -> list[int]:
        unique_ids = list(dict.fromkeys(value))
        if len(unique_ids) > 5:
            raise serializers.ValidationError("单个生成项最多支持 5 张图片。")
        return unique_ids


class GenerationItemBulkSerializer(serializers.Serializer):
    items = GenerationItemInputSerializer(many=True, allow_empty=False)


class GenerationItemSerializer(serializers.ModelSerializer):
    images = UploadedImageSerializer(many=True, read_only=True)
    image_ids = serializers.SerializerMethodField()

    class Meta:
        model = GenerationItem
        fields = ["id", "batch", "images", "image_ids", "title", "description", "sort_order", "is_combined", "created_at", "updated_at"]

    def get_image_ids(self, obj: GenerationItem) -> list[int]:
        return list(obj.images.values_list("id", flat=True))


class UploadRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadRecord
        fields = [
            "id",
            "batch",
            "draft",
            "question",
            "similar_questions",
            "answer_text",
            "image_cdn_urls",
            "wechat_image_items",
            "wechat_record_id",
            "wechat_record_values",
            "source_draft_ids",
            "ok",
            "response_summary",
            "created_at",
        ]


class LlmUsageLogSerializer(serializers.ModelSerializer):
    batch_title = serializers.CharField(source="batch.title", read_only=True)
    draft_question = serializers.CharField(source="draft.question", read_only=True)

    class Meta:
        model = LlmUsageLog
        fields = [
            "id",
            "batch",
            "batch_title",
            "draft",
            "draft_question",
            "model",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "ok",
            "error_message",
            "created_at",
        ]

