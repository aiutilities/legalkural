from pathlib import Path

from pypdf import PdfWriter

from aidpl.intake_worker import run_intake


def create_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)

    with path.open("wb") as handle:
        writer.write(handle)


def test_intake_rejects_pdf_without_text(tmp_path: Path) -> None:
    source = tmp_path / "blank.pdf"
    create_pdf(source)

    try:
        run_intake(
            source_pdf=source,
            case_id="LK-TEST-INTAKE-0001",
            case_root=tmp_path / "case",
            overwrite=False,
        )
    except ValueError as exc:
        assert "No embedded text" in str(exc)
    else:
        raise AssertionError("Blank PDF should require OCR.")
