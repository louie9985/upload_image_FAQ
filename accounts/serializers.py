from __future__ import annotations

from django.contrib.auth.models import User
from rest_framework import serializers


class CurrentUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    external_user_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "is_staff", "name", "avatar_url", "external_user_id"]

    def get_name(self, obj: User) -> str:
        profile = getattr(obj, "employee_profile", None)
        return profile.name if profile else obj.get_full_name()

    def get_avatar_url(self, obj: User) -> str:
        profile = getattr(obj, "employee_profile", None)
        return profile.avatar_url if profile else ""

    def get_external_user_id(self, obj: User) -> str:
        profile = getattr(obj, "employee_profile", None)
        return profile.external_user_id if profile else ""

