import json

import pytest

from aidpl.providers import ModelRequest, create_provider
from aidpl.providers.mock import MockProvider


def test_mock_text_response() -> None:
    provider = MockProvider()
    response = provider.generate(
        ModelRequest(
            agent_id="LK-TEST",
            task="Test text generation",
            system_prompt="System",
            user_prompt="User",
        )
    )

    assert response.provider == "mock"
    assert "LK-TEST" in response.text
    assert response.structured is None


def test_mock_structured_response() -> None:
    provider = MockProvider(
        fixture={
            "status": "PASS",
            "items": [1, 2, 3],
        }
    )
    response = provider.generate(
        ModelRequest(
            agent_id="LK-TEST",
            task="Test structured generation",
            system_prompt="System",
            user_prompt="Return JSON.",
            response_format="json",
        )
    )

    assert response.structured == {
        "status": "PASS",
        "items": [1, 2, 3],
    }
    assert json.loads(response.text)["status"] == "PASS"


def test_factory_supports_expected_providers() -> None:
    assert create_provider("mock").name == "mock"
    assert create_provider("openai").name == "openai"
    assert create_provider("deepseek").name == "deepseek"
    assert create_provider("qwen").name == "qwen"


def test_anthropic_is_explicitly_deferred() -> None:
    with pytest.raises(ValueError, match="reserved"):
        create_provider("anthropic")


def test_live_provider_health_does_not_call_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    health = create_provider("openai").health()

    assert health["configured"] is False
    assert health["status"] == "MISSING_API_KEY"
