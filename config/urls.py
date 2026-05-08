from __future__ import annotations

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts.views import AuthViewSet
from audit.views import AuditLogViewSet
from faq.views import BatchJobViewSet, FaqDraftViewSet, LlmUsageViewSet, UploadedImageViewSet, UploadRecordViewSet

router = DefaultRouter()
router.register("auth", AuthViewSet, basename="auth")
router.register("batches", BatchJobViewSet, basename="batch")
router.register("images", UploadedImageViewSet, basename="image")
router.register("drafts", FaqDraftViewSet, basename="draft")
router.register("upload-records", UploadRecordViewSet, basename="upload-record")
router.register("llm-usage", LlmUsageViewSet, basename="llm-usage")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

admin.site.site_header = "图片问答上传平台管理后台"
admin.site.site_title = "图片问答上传平台"
admin.site.index_title = "后台管理"


def api_health(_request):
    return JsonResponse({"service": "upload-image-faq-api", "ok": True})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("", api_health),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

