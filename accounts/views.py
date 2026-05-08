from __future__ import annotations

from django.contrib.auth import authenticate, login as auth_login, logout
from django.middleware.csrf import get_token
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.serializers import CurrentUserSerializer
from audit.services import log_action


class AuthViewSet(viewsets.ViewSet):
    def get_permissions(self):
        if self.action == "login":
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        get_token(request)
        return Response(CurrentUserSerializer(request.user).data)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        username = str(request.data.get("username", "")).strip()
        password = str(request.data.get("password", ""))
        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "账号或密码错误。"}, status=status.HTTP_400_BAD_REQUEST)

        auth_login(request, user)
        get_token(request)
        log_action(user, "login", "User", user.pk, request=request)
        return Response(CurrentUserSerializer(user).data)

    @action(detail=False, methods=["post"], url_path="logout")
    def logout(self, request):
        log_action(request.user, "logout", "User", request.user.pk, request=request)
        logout(request)
        return Response({"ok": True})

