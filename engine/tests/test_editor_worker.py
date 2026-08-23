import json
import re
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


def test_build_article_propagates_structured_law_and_enforces_title_only():
    from aidpl.editor_worker import build_article

    article = build_article(
        "LK-TEST",
        {"court": "Madras High Court", "judge": "Test Judge"},
        {"events": []},
        {"material_facts": []},
        {"issues": [{"question": "What tariff applies?"}]},
        {
            "documentary_evidence": [],
            "missing_evidence": [],
        },
        {
            "constitutional_provisions": [
                {
                    "article": "Article 14 (Constitution of India)",
                    "treatment": "discussed",
                    "how_court_used": "Used in the discrimination analysis.",
                }
            ],
            "statutes": [
                {
                    "name": "Example Municipal Act",
                    "section": "Section 2(1)",
                    "treatment": "relied-on",
                    "how_court_used": "Used to define residence.",
                }
            ],
            "regulations": [
                {
                    "name": "Example Regulations",
                    "provision": "Regulation 4(ii)",
                    "treatment": "rejected",
                    "how_court_used": "Commercial classification was rejected.",
                }
            ],
            "precedents": [
                {
                    "case_name": "Example v. State",
                    "citation": "2026 SCC Test 1",
                    "treatment": "relied-on",
                    "how_court_used": "Applied the recipient-perspective test.",
                }
            ],
        },
        {
            "reasoning_steps": [],
            "ratio_candidates": [],
        },
        {
            "outcome": "Allowed",
            "operative_directions": [],
            "limitations": [],
        },
        {
            "compressed_title": "Use Over Label",
            "legal_holding": "Residential end-use governs.",
            "universal_principle": "Function prevails over label.",
            "thirukkural_algorithm_usage": "TITLE_ONLY",
            "tamil_rendered": False,
        },
    )

    assert "Article 14 (Constitution of India)" in article
    assert "Used in the discrimination analysis." in article

    assert "Example Municipal Act — Section 2(1)" in article
    assert "Used to define residence." in article

    assert "Example Regulations — Regulation 4(ii)" in article
    assert "Commercial classification was rejected." in article

    assert "Example v. State — 2026 SCC Test 1" in article
    assert "Applied the recipient-perspective test." in article

    assert "Kural-Inspired" not in article
    assert not re.search(r"[\u0B80-\u0BFF]", article)
