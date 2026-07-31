from __future__ import annotations

import json
from typing import Any

from .base import ModelProvider, ModelRequest, ModelResponse


class MockProvider(ModelProvider):
    name = "mock"

    def __init__(
        self,
        model: str = "mock-legal-review-v1",
        fixture: dict[str, Any] | None = None,
    ) -> None:
        self.model = model
        self.fixture = fixture

    def generate(self, request: ModelRequest) -> ModelResponse:
        structured = self.fixture

        if request.response_format == "json":
            if structured is None:
                structured = {
                    "status": "MOCK_REVIEW_COMPLETE",
                    "agent_id": request.agent_id,
                    "task": request.task,
                }
            text = json.dumps(structured, ensure_ascii=False)
        else:
            text = (
                f"Mock response for {request.agent_id}: "
                f"{request.task}"
            )

        return ModelResponse(
            provider=self.name,
            model=self.model,
            text=text,
            structured=structured,
            request_id="mock-request-0001",
            usage={
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
            raw={
                "mock": True,
                "response_format": request.response_format,
            },
        )

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "model": self.model,
            "configured": True,
            "live_inference": False,
            "status": "READY",
        }
