from __future__ import annotations

from .base import ModelProvider
from .mock import MockProvider
from .openai_compatible import (
    create_deepseek_provider,
    create_qwen_provider,
)
from .openai_responses import OpenAIResponsesProvider


def create_provider(name: str) -> ModelProvider:
    normalized = name.strip().lower()

    if normalized == "mock":
        return MockProvider()

    if normalized == "openai":
        return OpenAIResponsesProvider()

    if normalized == "deepseek":
        return create_deepseek_provider()

    if normalized == "qwen":
        return create_qwen_provider()

    if normalized == "anthropic":
        raise ValueError(
            "Anthropic adapter is reserved for provider layer v0.2. "
            "Use mock, openai, deepseek or qwen."
        )

    raise ValueError(f"Unsupported provider: {name}")
