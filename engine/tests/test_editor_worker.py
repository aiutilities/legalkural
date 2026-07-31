import json
from pathlib import Path

from aidpl.editor_worker import run_editor


def test_run_editor(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    output = case_root / "output"

    artifacts = {
        "01-metadata/metadata.json": {
            "court": "Sample High Court",
            "judge": "Justice Sample"
        },
        "02-timeline/timeline.json": {"events": []},
        "03-facts/facts.json": {
            "material_facts": [{"text": "A material fact.", "source_pages": [1]}]
        },
        "04-issues/issues.json": {
            "issues": [{"question": "Whether the claim succeeds?", "source_pages": [2]}]
        },
        "05-evidence/evidence.json": {
            "documentary_evidence": [],
            "missing_evidence": []
        },
        "06-law/law.json": {
            "constitutional_provisions": [],
            "statutes": [],
            "regulations": [],
            "precedents": []
        },
        "07-reasoning/reasoning.json": {
            "reasoning_steps": [{"text": "The Court considered the evidence."}],
            "ratio_candidates": []
        },
        "08-decision/decision.json": {
            "outcome": "Allowed",
            "operative_directions": [{"text": "The petition is allowed."}],
            "limitations": []
        },
        "09-kural/kural-brief.json": {
            "compressed_title": "Proof Must Lead",
            "legal_holding": "The claim succeeds on proof.",
            "universal_principle": "Proof must guide judgment.",
            "kural_inspired_english": "Where proof leads, judgment follows."
        }
    }

    for relative, payload in artifacts.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    report = run_editor("LK-TEST-EDITOR-0001", case_root)

    assert report["status"] == "COMPLETE_WITH_QA_REQUIRED"
    assert report["word_count"] > 100
    article = (output / "10-article/article.md").read_text(encoding="utf-8")
    assert "Proof Must Lead" in article
    assert "not personalised legal advice" in article
