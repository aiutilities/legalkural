from pathlib import Path

import pytest

from aidpl.manual_tasks import create_task
from aidpl.orchestrator import build_plan, save_plan


WORKERS = [
    ("aidpl.editorial_review_worker", "run_review"),
    ("aidpl.extraction_review_worker", "run_review"),
    ("aidpl.kural_review_worker", "run_review"),
    ("aidpl.law_review_worker", "run_review"),
    ("aidpl.qa_review_worker", "run_review"),
    ("aidpl.reasoning_review_worker", "run_review"),
]


def prepare_case(tmp_path: Path) -> tuple[str, Path]:
    case_id = "LK-DIRECT-GATE-001"
    case_root = tmp_path / case_id
    case_root.mkdir()

    plan = build_plan(
        case_id=case_id,
        case_root=case_root,
    )

    save_plan(
        case_root / "aidpl-plan.json",
        plan,
    )

    create_task(
        case_root=case_root,
        case_id=case_id,
        task_type="LEGAL_FIDELITY_REVIEW",
        title="Human review required",
        instructions="Complete review before execution.",
        source_agent="LK-QA",
        blocking=True,
    )

    return case_id, case_root


@pytest.mark.parametrize(
    ("module_name", "function_name"),
    WORKERS,
)
def test_direct_review_gate_is_wired_before_provider_execution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
    function_name: str,
) -> None:
    import importlib
    import inspect

    module = importlib.import_module(module_name)

    source = inspect.getsource(
        getattr(module, function_name)
    )

    assert (
        source.index(
            "assert_manual_execution_allowed(plan)"
        )
        <
        source.index(
            "create_provider(provider_name)"
        )
    )


@pytest.mark.parametrize(
    "module_name",
    [item[0] for item in WORKERS],
)
def test_open_blocking_task_prevents_provider_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    import importlib

    case_id, case_root = prepare_case(tmp_path)

    module = importlib.import_module(module_name)

    called = False

    def forbidden_provider(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError(
            "provider must not be created while manual gate is open"
        )

    monkeypatch.setattr(
        module,
        "create_provider",
        forbidden_provider,
    )

    root = Path(__file__).resolve().parents[1]

    kwargs = {
        "case_id": case_id,
        "case_root": case_root,
        "schema_root": root / "schemas",
        "provider_name": "mock",
        "allow_live": False,
        "max_source_characters": 1000,
    }

    import inspect

    sig = inspect.signature(module.run_review)

    kwargs = {
        key: value
        for key, value in kwargs.items()
        if key in sig.parameters
    }

    with pytest.raises(
        ValueError,
        match="OPEN blocking manual task prevents execution",
    ):
        module.run_review(**kwargs)

    assert called is False
