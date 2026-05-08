from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from openai import OpenAI


@dataclass(frozen=True)
class GeneratedFaq:
    question: str
    similar_questions: list[str]
    answer_text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    usage_detail: dict[str, Any] | None = None


class LLMClient:
    def generate(self, *, description: str, image_name: str) -> GeneratedFaq:
        api_key = settings.LLM_API_KEY or settings.DEEPSEEK_API_KEY
        if not api_key:
            raise RuntimeError("缺少 LLM_API_KEY 或 DEEPSEEK_API_KEY，请先在 .env 中配置。")

        client = OpenAI(api_key=api_key, base_url=settings.LLM_BASE_URL, timeout=settings.LLM_TIMEOUT_SECONDS)
        min_similar, max_similar = _get_similar_questions_range()
        messages = [
            {"role": "system", "content": build_system_prompt(min_similar=min_similar, max_similar=max_similar)},
            {"role": "user", "content": build_user_prompt(description=description, image_name=image_name, min_similar=min_similar, max_similar=max_similar)},
        ]

        last_error: Exception | None = None
        for attempt in range(1, settings.LLM_RETRY_COUNT + 1):
            try:
                response = client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    stream=False,
                    reasoning_effort=settings.LLM_REASONING_EFFORT,
                    response_format={"type": "json_object"},
                    extra_body={"thinking": {"type": "enabled"}},
                )
                content = response.choices[0].message.content
                if not content:
                    raise RuntimeError("大模型返回内容为空。")
                generated = parse_generated_json(json.loads(content), description)
                usage_detail = _usage_to_dict(response.usage)
                return GeneratedFaq(
                    question=generated.question,
                    similar_questions=generated.similar_questions,
                    answer_text=generated.answer_text,
                    model=settings.LLM_MODEL,
                    prompt_tokens=int(usage_detail.get("prompt_tokens") or 0),
                    completion_tokens=int(usage_detail.get("completion_tokens") or 0),
                    total_tokens=int(usage_detail.get("total_tokens") or 0),
                    usage_detail=usage_detail,
                )
            except Exception as exc:  # noqa: BLE001 - keep final failure for task status.
                last_error = exc
                if attempt < settings.LLM_RETRY_COUNT:
                    time.sleep(attempt)

        raise RuntimeError(f"大模型生成失败：{last_error}") from last_error


def parse_generated_json(raw: dict, description: str) -> GeneratedFaq:
    min_similar, max_similar = _get_similar_questions_range()
    question = str(raw.get("question", "")).strip()[:200]
    answer_text = str(raw.get("answer_text", "")).strip()[:500]
    similar_raw = raw.get("similar_questions", [])
    if isinstance(similar_raw, str):
        similar_raw = [line.strip() for line in similar_raw.splitlines() if line.strip()]
    similar_questions = [str(item).strip()[:200] for item in similar_raw if str(item).strip()][:max_similar]

    if not question:
        question = f"{description[:80]}相关图片可以看一下吗？"
    if not answer_text:
        answer_text = f"图片说明：{description}。具体信息请以实际材料为准。"
    if len(similar_questions) < min_similar:
        similar_questions.extend(_fallback_similar_questions(description, question, target=min_similar))

    return GeneratedFaq(question=question, similar_questions=similar_questions[:max_similar], answer_text=answer_text, model="")


def _usage_to_dict(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return usage
    return {}


def _fallback_similar_questions(description: str, question: str, *, target: int) -> list[str]:
    short = description[:60] or "这张图片"
    base = [
        question,
        f"{short}是什么？",
        f"可以介绍一下{short}吗？",
        f"这张{short}图片表达的内容是什么？",
        f"我想了解{short}相关信息。",
    ]
    while len(base) < target:
        base.append(f"{short}有哪些关键信息？")
    return base


def _get_similar_questions_range() -> tuple[int, int]:
    min_similar = int(getattr(settings, "LLM_SIMILAR_QUESTIONS_MIN", 5) or 5)
    max_similar = int(getattr(settings, "LLM_SIMILAR_QUESTIONS_MAX", 10) or 10)
    min_similar = max(1, min_similar)
    max_similar = max(min_similar, max_similar)
    return min_similar, max_similar


def build_system_prompt(*, min_similar: int, max_similar: int) -> str:
    return f"""你是企业内部知识库问答对生成助手。
请根据员工填写的图片描述和图片文件名，生成适合上传到企业智能表格的问答内容。
要求：
1. 严格依据描述，不要编造描述之外的业务事实。
2. 输出 1 个主问题、{min_similar}-{max_similar} 个相似问题、1 段 500 字以内答案。
3. 问题要口语化，适合员工查询。
4. 严格输出 JSON，不要输出 Markdown 或解释文字。
"""


def build_user_prompt(*, description: str, image_name: str, min_similar: int, max_similar: int) -> str:
    return f"""图片文件名：{image_name}
员工填写的图片描述：{description}

输出 JSON schema：
{{
  "question": "主问题，最多 200 字",
  "similar_questions": ["{min_similar}-{max_similar} 条相似问法"],
  "answer_text": "答案文字，最多 500 字"
}}
"""

