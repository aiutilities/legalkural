from __future__ import annotations

import json
import os
from typing import Any

from .base import ModelProvider, ModelRequest, ModelResponse
from .http import post_json


class OpenAICompatibleProvider(ModelProvider):
    def __init__(
        self,
        provider_name: str,
        api_key_env: str,
        model_env: str,
        base_url_env: str,
        default_model: str,
        default_base_url: str,
        timeout_seconds: int = 120,
    ) -> None:
        self.name = provider_name
        self.api_key_env = api_key_env
        self.api_key = os.getenv(api_key_env)
        self.model = os.getenv(model_env, default_model)
        self.base_url = os.getenv(
            base_url_env,
            default_base_url,
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _require_configuration(self) -> None:
        if not self.api_key:
            raise ValueError(
                f"{self.api_key_env} is required "
                f"for provider={self.name}."
            )

    def generate(self, request: ModelRequest) -> ModelResponse:
        self._require_configuration()

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                {
                    "role": "user",
                    "content": request.user_prompt,
                },
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }

        if request.response_format == "json":
            payload["response_format"] = {
                "type": "json_object",
            }

        raw, headers = post_json(
            url=f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )

        choices = raw.get("choices") or []

        if not choices:
            raise ValueError(
                f"{self.name} returned no completion choices."
            )

        text = (
            choices[0]
            .get("message", {})
            .get("content")
            or ""
        )

        structured = None

        if request.response_format == "json":
            structured = json.loads(text)

        return ModelResponse(
            provider=self.name,
            model=raw.get("model") or self.model,
            text=text,
            structured=structured,
            request_id=(
                headers.get("x-request-id")
                or raw.get("id")
            ),
            usage=raw.get("usage") or {},
            raw=raw,
        )

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "base_url": self.base_url,
            "configured": bool(self.api_key),
            "live_inference": True,
            "status": "READY" if self.api_key else "MISSING_API_KEY",
        }


def create_deepseek_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        provider_name="deepseek",
        api_key_env="DEEPSEEK_API_KEY",
        model_env="DEEPSEEK_MODEL",
        base_url_env="DEEPSEEK_BASE_URL",
        default_model="deepseek-v4-pro",
        default_base_url="https://api.deepseek.com",
    )


def create_qwen_provider() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        provider_name="qwen",
        api_key_env="DASHSCOPE_API_KEY",
        model_env="QWEN_MODEL",
        base_url_env="QWEN_BASE_URL",
        default_model="qwen3.7-plus",
        default_base_url=(
            "https://dashscope-us.aliyuncs.com/"
            "compatible-mode/v1"
        ),
    )
