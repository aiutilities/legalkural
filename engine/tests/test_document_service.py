from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter

from publishing.document_service import (
    DocumentProcessingError,
    detect_format,
    generate_qr,
    process_document,
    sha256_file,
    slugify,
    validate_pdf,
)


def create_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)

    with path.open("wb") as handle:
        writer.write(handle)


def test_slugify() -> None:
    assert slugify("Government Order 2026!") == (
        "government-order-2026"
    )


def test_detect_format() -> None:
    assert detect_format(Path("judgment.pdf")) == "PDF"
    assert detect_format(Path("order.docx")) == "DOCX"
    assert detect_format(Path("data.xlsx")) == "XLSX"


def test_reject_unsupported_format() -> None:
    with pytest.raises(
        DocumentProcessingError,
        match="Unsupported",
    ):
        detect_format(Path("unsafe.exe"))


def test_validate_pdf(tmp_path: Path) -> None:
    path = tmp_path / "test.pdf"
    create_pdf(path)

    assert validate_pdf(path) == 1


def test_generate_qr(tmp_path: Path) -> None:
    output = tmp_path / "qr.png"

    generate_qr(
        "https://example.com/documents/test.pdf",
        output,
    )

    assert output.exists()
    assert output.stat().st_size > 0


def test_sha256_file(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("LegalKural", encoding="utf-8")

    assert len(sha256_file(path)) == 64


def test_process_pdf_document(tmp_path: Path) -> None:
    source = tmp_path / "judgment.pdf"
    create_pdf(source)

    result, payload = process_document(
        source=source,
        output_root=tmp_path / "documents",
        title="Test Judgment",
        document_type="JUDGMENT",
        uploaded_by="admin",
        download_base_url="https://example.com/downloads",
    )

    assert result.pdf_path.exists()
    assert result.qr_path.exists()
    assert result.page_count == 1
    assert result.conversion_status == "NOT_REQUIRED"
    assert payload["approval_status"] == "DRAFT"
    assert payload["published_filename"] == "test-judgment.pdf"
