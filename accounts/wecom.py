from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import requests
from django.conf import settings


@dataclass(frozen=True)
class WeComUserInfo:
    external_user_id: str
    name: str = ""
    avatar_url: str = ""
    department: str = ""
    raw_profile: dict | None = None


class WeComOAuthClient:
    authorize_url = "https://open.weixin.qq.com/connect/oauth2/authorize"
    token_url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
    user_info_url = "https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo"
    user_detail_url = "https://qyapi.weixin.qq.com/cgi-bin/user/get"

    def build_authorize_url(self, state: str) -> str:
        query = urlencode(
            {
                "appid": settings.WECHAT_CORP_ID,
                "redirect_uri": settings.WECHAT_REDIRECT_URI,
                "response_type": "code",
                "scope": "snsapi_base",
                "state": state,
                "agentid": settings.WECHAT_AGENT_ID,
            }
        )
        return f"{self.authorize_url}?{query}#wechat_redirect"

    def fetch_user(self, code: str) -> WeComUserInfo:
        access_token = self._fetch_access_token()
        response = requests.get(
            self.user_info_url,
            params={"access_token": access_token, "code": code},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"企业微信 OAuth 获取用户失败：{data}")

        user_id = data.get("userid") or data.get("UserId")
        if not user_id:
            raise RuntimeError(f"企业微信 OAuth 返回缺少 userid：{data}")

        detail = self._fetch_user_detail(access_token, user_id)
        return WeComUserInfo(
            external_user_id=user_id,
            name=detail.get("name", ""),
            avatar_url=detail.get("avatar", ""),
            department=",".join(str(item) for item in detail.get("department", [])),
            raw_profile=detail or data,
        )

    def _fetch_access_token(self) -> str:
        response = requests.get(
            self.token_url,
            params={"corpid": settings.WECHAT_CORP_ID, "corpsecret": settings.WECHAT_SECRET},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errcode", 0) != 0:
            raise RuntimeError(f"企业微信 access_token 获取失败：{data}")
        return data["access_token"]

    def _fetch_user_detail(self, access_token: str, user_id: str) -> dict:
        response = requests.get(
            self.user_detail_url,
            params={"access_token": access_token, "userid": user_id},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("errcode", 0) != 0:
            return {}
        return data

