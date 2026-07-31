from __future__ import annotations

import json
import os
from typing import Any

from .base import ModelProvider, ModelRequest, ModelResponse
from .http import post_json


class OpenAIResponsesProvider(ModelProvider):
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout_seconds: int = 120,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv(
            "OPENAI_MODEL",
            "gpt-5",
        )
        self.base_url = (
            base_url
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _require_configuration(self) -> None:
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is required for provider=openai."
            )

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str):
            return direct

        parts: list[str] = []

        for item in payload.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)

        return "\n".join(parts).strip()

    def generate(self, request: ModelRequest) -> ModelResponse:
        self._require_configuration()

        input_text = "\n\n".join(
            [
                f"SYSTEM:\n{request.system_prompt}",
                f"USER:\n{request.user_prompt}",
            ]
        )

        payload: dict[str, Any] = {
            "model": self.model,
            "input": input_text,
            "max_output_tokens": request.max_output_tokens,
            "metadata": request.metadata,
        }

        if request.response_format == "json":
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "legal_kural_agent_output",
                    "strict": True,
                    "schema": request.json_schema or {
                        "type": "object",
                        "additionalProperties": True,
                    },
                }
            }

        raw, headers = post_json(
            url=f"{self.base_url}/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            payload=payload,
            timeout_seconds=self.timeout_seconds,
        )

        text = self._extract_text(raw)
        structured = None

        if request.response_format == "json":
            structured = json.loads(text)

        usage = raw.get("usage") or {}

        return ModelResponse(
            provider=self.name,
            model=raw.get("model") or self.model,
            text=text,
            structured=structured,
            request_id=(
                headers.get("x-request-id")
                or raw.get("id")
            ),
            usage=usage,
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
