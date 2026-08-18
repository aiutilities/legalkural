import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

from journal.assembly import (
    assemble_journal,
    compute_assembly_sha256,
)
from journal.manifest import finalize_manifest
from journal.renderer import (
    extract_english_article_blocks,
    render_journal_pdf,
)


HTML = """
<p><strong>Name may call it trade; need makes it home.</strong></p>
<p>வியாபாரம் பெயர் பொருளன்று; பயன்தான் பொருள்.</p>
<p>This preamble is not part of the print journal.</p>
<h2>Case Snapshot</h2>
<p>The Court examined the actual residential end-use.</p>
<h2>Decision</h2>
<ul><li>The petitions were allowed.</li></ul>
"""


def assembly_fixture(root: Path):
    payload = (
        root
        / "generated"
        / "LK-0001"
        / "output"
        / "11-publication"
        / "wordpress-final-draft-payload.json"
    )
    payload.parent.mkdir(parents=True)
    payload.write_text(
        json.dumps(
            {
                "title": "End-Use Over Label: Hostels Are Homes",
                "slug": "end-use-over-label-hostels-are-homes",
                "excerpt": "A legal explainer.",
                "content": HTML,
            }
        ),
        encoding="utf-8",
    )

    manifest = finalize_manifest(
        journal_id="LK-JOURNAL-TEST",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal — Pilot",
        selected_by="Founder",
        finalized_at_utc="2026-08-18T04:00:00Z",
        articles=[
            {
                "case_id": "LK-0001",
                "title": "End-Use Over Label: Hostels Are Homes",
                "slug": "end-use-over-label-hostels-are-homes",
                "source_payload": payload.relative_to(root).as_posix(),
                "content_sha256": hashlib.sha256(
                    HTML.encode("utf-8")
                ).hexdigest(),
            }
        ],
    )
    return assemble_journal(manifest, project_root=root)


def test_extracts_only_substantive_english_blocks():
    blocks = extract_english_article_blocks(HTML)
    text = " ".join(value for _, value in blocks)

    assert blocks[0] == ("h2", "Case Snapshot")
    assert "Name may call it trade" not in text
    assert "வியாபாரம்" not in text
    assert "petitions were allowed" in text


def test_pdf_rendering_is_byte_deterministic(tmp_path):
    assembly = assembly_fixture(tmp_path)
    first = tmp_path / "first.pdf"
    second = tmp_path / "second.pdf"

    first_report = render_journal_pdf(assembly, first)
    second_report = render_journal_pdf(assembly, second)

    assert first.read_bytes() == second.read_bytes()
    assert first_report["pdf_sha256"] == second_report["pdf_sha256"]
    assert first_report["tamil_rendered"] is False


def test_pdf_is_structurally_readable(tmp_path):
    assembly = assembly_fixture(tmp_path)
    output = tmp_path / "journal.pdf"

    report = render_journal_pdf(assembly, output)
    reader = PdfReader(str(output))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)

    normalized_text = " ".join(text.split())

    assert report["page_count"] >= 2
    assert "LegalKural Weekly Journal - Pilot" in normalized_text
    assert "End-Use Over Label: Hostels Are Homes" in normalized_text
    assert "Case Snapshot" in normalized_text
    assert "petitions were allowed" in normalized_text
    assert "Name may call it trade" not in normalized_text
    assert "வியாபாரம்" not in normalized_text


def test_long_legal_sentence_remains_inside_print_boundary(tmp_path):
    long_text = (
        "In plain terms, natural justice requires that before a decision "
        "adversely affecting rights or liabilities is taken, such as "
        "enhancing a tariff by reclassification, the affected party "
        "should be informed and heard."
    )
    content = f"<h2>Natural Justice</h2><p>{long_text}</p>"

    payload = (
        tmp_path
        / "generated"
        / "LK-LONG"
        / "output"
        / "11-publication"
        / "wordpress-final-draft-payload.json"
    )
    payload.parent.mkdir(parents=True)
    payload.write_text(
        json.dumps(
            {
                "title": "Natural Justice Before Reclassification",
                "slug": "natural-justice-before-reclassification",
                "excerpt": "Print-boundary test.",
                "content": content,
            }
        ),
        encoding="utf-8",
    )

    manifest = finalize_manifest(
        journal_id="LK-JOURNAL-LONG-LINE",
        edition_date="2026-08-23",
        title="LegalKural Weekly Journal",
        selected_by="Founder",
        finalized_at_utc="2026-08-18T04:15:00Z",
        articles=[
            {
                "case_id": "LK-LONG",
                "title": "Natural Justice Before Reclassification",
                "slug": "natural-justice-before-reclassification",
                "source_payload": payload.relative_to(tmp_path).as_posix(),
                "content_sha256": hashlib.sha256(
                    content.encode("utf-8")
                ).hexdigest(),
            }
        ],
    )

    assembly = assemble_journal(manifest, project_root=tmp_path)
    output = tmp_path / "long-line.pdf"
    render_journal_pdf(assembly, output)

    extracted = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(str(output)).pages
    )

    normalized_extracted = " ".join(extracted.split())
    assert "should be informed and heard." in normalized_extracted


def test_pdf_embeds_portable_fonts(tmp_path):
    assembly = assembly_fixture(tmp_path)
    output = tmp_path / "embedded-fonts.pdf"

    render_journal_pdf(assembly, output)

    reader = PdfReader(str(output))
    embedded_font_streams = 0

    for page in reader.pages:
        fonts = page["/Resources"].get("/Font", {})
        for reference in fonts.values():
            font = reference.get_object()
            descriptor_reference = font.get("/FontDescriptor")
            if descriptor_reference is None:
                continue
            descriptor = descriptor_reference.get_object()
            if (
                descriptor.get("/FontFile")
                or descriptor.get("/FontFile2")
                or descriptor.get("/FontFile3")
            ):
                embedded_font_streams += 1

    assert embedded_font_streams > 0


def test_all_visible_pdf_text_uses_embedded_fonts(tmp_path):
    assembly = assembly_fixture(tmp_path)

    # Force enough repeated content to cross a page boundary.
    assembly["articles"][0]["content_html"] = (
        "<h2>Long Section</h2>"
        + "".join(
            "<p>The Court considered residential end-use, natural "
            "justice, maintainability and the operative directions.</p>"
            for _ in range(80)
        )
    )
    assembly["articles"][0]["content_sha256"] = hashlib.sha256(
        assembly["articles"][0]["content_html"].encode("utf-8")
    ).hexdigest()
    assembly["assembly_sha256"] = compute_assembly_sha256(assembly)

    output = tmp_path / "embedded-across-pages.pdf"
    render_journal_pdf(assembly, output)

    reader = PdfReader(str(output))
    unembedded_visible_fragments = []

    def inspect_text(text, cm, tm, font_dict, font_size):
        if not text.strip() or font_dict is None:
            return

        descriptor_reference = font_dict.get("/FontDescriptor")
        if descriptor_reference is None:
            unembedded_visible_fragments.append(text)
            return

        descriptor = descriptor_reference.get_object()
        embedded = any(
            descriptor.get(key) is not None
            for key in ("/FontFile", "/FontFile2", "/FontFile3")
        )
        if not embedded:
            unembedded_visible_fragments.append(text)

    for page in reader.pages:
        page.extract_text(visitor_text=inspect_text)

    assert unembedded_visible_fragments == []
