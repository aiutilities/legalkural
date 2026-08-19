from pathlib import Path
from pypdf import PdfReader
from journal.assembly import compute_assembly_sha256
from journal.renderer import BRAND_TAGLINE, RENDERER_VERSION, render_journal_pdf


def brand_assembly():
    value = {
        "schema_version": "1.0",
        "journal_id": "LK-JOURNAL-BRAND-0001",
        "edition_date": "2026-08-19",
        "covered_date_range": {"start": "2026-08-18", "end": "2026-08-18"},
        "title": "LegalKural Weekly Journal",
        "article_count": 1,
        "language": "en",
        "manifest_sha256": "a" * 64,
        "rendering_policy": {
            "body_language": "en",
            "tamil_rendering": False,
            "thirukkural_algorithm_usage": "TITLE_ONLY",
            "website_dressing": "DEFERRED_TO_FINAL_SPRINT",
        },
        "articles": [{
            "position": 1,
            "case_id": "LK-BRAND-CASE-0001",
            "title": "Meaning Beyond the Court Record",
            "published_at": "2026-08-18T12:00:00Z",
            "content_html": "<h2>Case Snapshot</h2><p>The court records events.</p><h3>Legal Principle</h3><p>LegalKural reveals their meaning.</p>",
        }],
    }
    value["assembly_sha256"] = compute_assembly_sha256(value)
    return value


def pdf_text(path: Path):
    return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)


def test_brand_cover_contents_and_hierarchy(tmp_path):
    output = tmp_path / "journal.pdf"
    evidence = render_journal_pdf(brand_assembly(), output)
    extracted = pdf_text(output)
    for expected in ("LegalKural", BRAND_TAGLINE, "Contents", "ARTICLE 1", "LK-JOURNAL-BRAND-0001", "Case Snapshot"):
        assert expected in extracted
    assert evidence["renderer_version"] == "2.0.0"


def test_brand_renderer_is_byte_deterministic(tmp_path):
    first, second = tmp_path / "first.pdf", tmp_path / "second.pdf"
    one = render_journal_pdf(brand_assembly(), first)
    two = render_journal_pdf(brand_assembly(), second)
    assert first.read_bytes() == second.read_bytes()
    assert one["pdf_sha256"] == two["pdf_sha256"]
    assert RENDERER_VERSION == "2.0.0"
