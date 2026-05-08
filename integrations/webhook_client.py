from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from django.conf import settings

from integrations.image_utils import to_base64_jpeg


@dataclass(frozen=True)
class WebhookUploadResult:
    ok: bool
    record_id: str = ""
    cdn_urls: list[str] | None = None
    image_items: list[dict[str, Any]] | None = None
    record_values: dict[str, Any] | None = None
    response: dict[str, Any] | None = None


class WebhookClient:
    def upload_one(
        self,
        *,
        webhook_url: str,
        question: str,
        similar_questions: list[str],
        answer_text: str,
        image_paths: list[Path],
    ) -> WebhookUploadResult:
        payload = {
            "add_records": [
                {
                    "values": {
                        settings.WECHAT_FIELD_MAP["question"]: question,
                        settings.WECHAT_FIELD_MAP["similar_questions"]: "\n".join(similar_questions),
                        settings.WECHAT_FIELD_MAP["answer_text"]: answer_text,
                        settings.WECHAT_FIELD_MAP["answer_images"]: [to_base64_jpeg(path) for path in image_paths],
                    }
                }
            ]
        }
        response_data: dict[str, Any] = {}
        for attempt in range(1, 4):
            try:
                response = requests.post(webhook_url, json=payload, timeout=60)
                response_data = {"status_code": response.status_code, "text": response.text}
                if response.ok:
                    parsed = _parse_json(response.text)
                    if parsed.get("errcode", 0) == 0:
                        record = (parsed.get("add_records") or [{}])[0]
                        values = record.get("values", {})
                        images = values.get(settings.WECHAT_FIELD_MAP["answer_images"], [])
                        image_items = [_clean_image_item(item) for item in images if isinstance(item, dict)]
                        return WebhookUploadResult(
                            ok=True,
                            record_id=record.get("record_id", ""),
                            cdn_urls=[item["image_url"] for item in image_items if item.get("image_url")],
                            image_items=image_items,
                            record_values=values,
                            response=parsed,
                        )
                    response_data = parsed
            except Exception as exc:  # noqa: BLE001 - final response is persisted.
                response_data = {"error": str(exc)}
            if attempt < 3:
                time.sleep(attempt)
        return WebhookUploadResult(ok=False, cdn_urls=[], image_items=[], record_values={}, response=response_data)


def _parse_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def _clean_image_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id", ""),
        "title": item.get("title", ""),
        "image_url": item.get("image_url", ""),
        "width": item.get("width"),
        "height": item.get("height"),
    }

