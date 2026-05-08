from __future__ import annotations

from django.contrib import admin

from faq.models import BatchJob, FaqDraft, GenerationItem, LlmUsageLog, UploadedImage, UploadRecord, WebhookConfig


class UploadedImageInline(admin.TabularInline):
    model = UploadedImage
    extra = 0
    fields = ("original_name", "description", "sort_order", "created_at")
    readonly_fields = ("created_at",)


class FaqDraftInline(admin.TabularInline):
    model = FaqDraft
    extra = 0
    fields = ("generation_item", "question", "status", "is_edited", "error_message", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(BatchJob)
class BatchJobAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "status", "total_count", "processed_count", "failed_count", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("title", "owner__username")
    inlines = [UploadedImageInline, FaqDraftInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(UploadedImage)
class UploadedImageAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "original_name", "sort_order", "created_at")
    search_fields = ("original_name", "description")
    readonly_fields = ("created_at",)


@admin.register(FaqDraft)
class FaqDraftAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "generation_item", "question", "status", "is_edited", "updated_at")
    list_filter = ("status", "is_edited")
    search_fields = ("question", "answer_text")
    readonly_fields = ("created_at", "updated_at")


@admin.register(GenerationItem)
class GenerationItemAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "title", "is_combined", "sort_order", "updated_at")
    list_filter = ("is_combined", "created_at")
    search_fields = ("title", "description", "batch__title")
    readonly_fields = ("created_at", "updated_at")


@admin.register(WebhookConfig)
class WebhookConfigAdmin(admin.ModelAdmin):
    list_display = ("owner", "display_masked_url", "updated_at")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="脱敏 Webhook 链接")
    def display_masked_url(self, obj: WebhookConfig) -> str:
        return obj.masked_url()


@admin.register(UploadRecord)
class UploadRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "question", "ok", "wechat_record_id", "created_at")
    list_filter = ("ok", "created_at")
    search_fields = ("question", "wechat_record_id")
    readonly_fields = ("created_at", "source_draft_ids", "image_cdn_urls", "wechat_image_items", "wechat_record_values", "response_summary")


@admin.register(LlmUsageLog)
class LlmUsageLogAdmin(admin.ModelAdmin):
    list_display = ("id", "batch", "draft", "model", "prompt_tokens", "completion_tokens", "total_tokens", "ok", "created_at")
    list_filter = ("ok", "model", "created_at")
    search_fields = ("model", "error_message", "draft__question")
    readonly_fields = ("created_at",)

