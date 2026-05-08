from __future__ import annotations

from django.conf import settings
from django.db import models


class BatchJob(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        GENERATING = "generating", "生成中"
        GENERATED = "generated", "已生成"
        UPLOADING = "uploading", "上传中"
        COMPLETED = "completed", "已完成"
        FAILED = "failed", "失败"

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="创建人", on_delete=models.CASCADE, related_name="faq_batches")
    title = models.CharField("任务标题", max_length=128, blank=True)
    status = models.CharField("任务状态", max_length=32, choices=Status.choices, default=Status.DRAFT)
    total_count = models.PositiveIntegerField("总数", default=0)
    processed_count = models.PositiveIntegerField("已处理数", default=0)
    failed_count = models.PositiveIntegerField("失败数", default=0)
    current_step = models.CharField("当前步骤", max_length=255, blank=True)
    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "批量任务"
        verbose_name_plural = "批量任务"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title or f"批量任务 {self.pk}"


class UploadedImage(models.Model):
    batch = models.ForeignKey(BatchJob, verbose_name="所属任务", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField("本地图片", upload_to="faq_images/%Y/%m/%d/")
    original_name = models.CharField("原始文件名", max_length=255)
    description = models.TextField("图片描述", blank=True)
    sort_order = models.PositiveIntegerField("排序", default=0)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "上传图片"
        verbose_name_plural = "上传图片"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.original_name


class GenerationItem(models.Model):
    batch = models.ForeignKey(BatchJob, verbose_name="所属任务", on_delete=models.CASCADE, related_name="generation_items")
    images = models.ManyToManyField(UploadedImage, verbose_name="关联图片", related_name="generation_items")
    title = models.CharField("生成项名称", max_length=128)
    description = models.TextField("生成项描述")
    sort_order = models.PositiveIntegerField("排序", default=0)
    is_combined = models.BooleanField("是否合并项", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "生成项"
        verbose_name_plural = "生成项"
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.title


class FaqDraft(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待生成"
        GENERATED = "generated", "已生成"
        FAILED = "failed", "失败"

    batch = models.ForeignKey(BatchJob, verbose_name="所属任务", on_delete=models.CASCADE, related_name="drafts")
    image = models.ForeignKey(UploadedImage, verbose_name="首张图片", on_delete=models.SET_NULL, null=True, blank=True, related_name="drafts")
    generation_item = models.OneToOneField(GenerationItem, verbose_name="生成项", on_delete=models.CASCADE, null=True, blank=True, related_name="draft")
    question = models.CharField("主问题", max_length=200, blank=True)
    similar_questions = models.JSONField("相似问题", default=list, blank=True)
    answer_text = models.TextField("答案", blank=True)
    status = models.CharField("生成状态", max_length=32, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField("错误信息", blank=True)
    is_edited = models.BooleanField("是否人工编辑", default=False)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "问答草稿"
        verbose_name_plural = "问答草稿"
        ordering = ["generation_item__sort_order", "image__sort_order", "id"]

    def __str__(self) -> str:
        return self.question or f"问答草稿 {self.pk}"


class WebhookConfig(models.Model):
    owner = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="用户", on_delete=models.CASCADE, related_name="webhook_config")
    webhook_url = models.URLField("Webhook 链接")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    class Meta:
        verbose_name = "Webhook 配置"
        verbose_name_plural = "Webhook 配置"

    def masked_url(self) -> str:
        if "key=" not in self.webhook_url:
            return self.webhook_url[:24] + "***"
        prefix, _, key = self.webhook_url.partition("key=")
        return f"{prefix}key={key[:6]}***{key[-4:]}"


class UploadRecord(models.Model):
    batch = models.ForeignKey(BatchJob, verbose_name="所属任务", on_delete=models.CASCADE, related_name="upload_records")
    draft = models.ForeignKey(FaqDraft, verbose_name="问答草稿", on_delete=models.SET_NULL, null=True, blank=True, related_name="upload_records")
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name="上传人", on_delete=models.SET_NULL, null=True, blank=True)
    question = models.CharField("主问题", max_length=200)
    similar_questions = models.JSONField("相似问题", default=list)
    answer_text = models.TextField("答案")
    image_cdn_urls = models.JSONField("图片 CDN 链接", default=list, blank=True)
    wechat_image_items = models.JSONField("企业微信图片返回项", default=list, blank=True)
    wechat_record_id = models.CharField("企业微信记录 ID", max_length=64, blank=True)
    wechat_record_values = models.JSONField("企业微信记录字段", default=dict, blank=True)
    source_draft_ids = models.JSONField("来源草稿 ID", default=list, blank=True)
    ok = models.BooleanField("是否成功", default=False)
    response_summary = models.JSONField("Webhook 完整响应", default=dict, blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "上传记录"
        verbose_name_plural = "上传记录"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.question


class LlmUsageLog(models.Model):
    batch = models.ForeignKey(BatchJob, verbose_name="所属任务", on_delete=models.CASCADE, related_name="llm_usage_logs")
    draft = models.ForeignKey(FaqDraft, verbose_name="问答草稿", on_delete=models.SET_NULL, null=True, blank=True, related_name="llm_usage_logs")
    model = models.CharField("模型", max_length=128)
    prompt_tokens = models.PositiveIntegerField("输入 Token", default=0)
    completion_tokens = models.PositiveIntegerField("输出 Token", default=0)
    total_tokens = models.PositiveIntegerField("总 Token", default=0)
    usage_detail = models.JSONField("Token 明细", default=dict, blank=True)
    ok = models.BooleanField("是否成功", default=False)
    error_message = models.TextField("错误信息", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        verbose_name = "AI Token 用量"
        verbose_name_plural = "AI Token 用量"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.model} {self.total_tokens} tokens"

