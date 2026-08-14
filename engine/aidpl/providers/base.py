from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ModelRequest:
    agent_id: str
    task: str
    system_prompt: str
    user_prompt: str
    response_format: str = "text"
    json_schema: dict[str, Any] | None = None
    json_schema_strict: bool = True
    temperature: float = 0.0
    max_output_tokens: int = 4096
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    model: str
    text: str
    structured: dict[str, Any] | list[Any] | None
    request_id: str | None
    usage: dict[str, Any]
    raw: dict[str, Any]


class ModelProvider(ABC):
    name: str

    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a text or structured response."""

    @abstractmethod
    def health(self) -> dict[str, Any]:
        """Return configuration and availability details without inference."""
