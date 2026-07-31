from pathlib import Path

from aidpl.extraction_worker import (
    extract_metadata,
    load_pages,
    run_extraction,
)


def sample_source() -> str:
    return """<PAGE:1>
IN THE HIGH COURT OF JUDICATURE AT MADRAS
Reserved on 29.08.2025
Pronounced on 07.11.2025
THE HON'BLE MR. JUSTICE SAMPLE JUDGE
W.P.No.10194 of 2025
</PAGE:1>

<PAGE:2>
The main issues are as follows:
Whether the property should be treated as commercial premises?
The petitioners have been running hostels.
</PAGE:2>
"""


def test_load_pages(tmp_path: Path) -> None:
    source = tmp_path / "source-text.txt"
    source.write_text(sample_source(), encoding="utf-8")

    pages = load_pages(source)

    assert len(pages) == 2
    assert pages[0]["page"] == 1


def test_extract_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source-text.txt"
    source.write_text(sample_source(), encoding="utf-8")
    pages = load_pages(source)

    metadata = extract_metadata("LK-TEST-0001", pages)

    assert metadata["court"] == "High Court of Judicature at Madras"
    assert metadata["dates"]["reserved_on"] == "2025-08-29"
    assert metadata["dates"]["pronounced_on"] == "2025-11-07"


def test_run_extraction(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    working = case_root / "working"
    working.mkdir(parents=True)
    (working / "source-text.txt").write_text(
        sample_source(),
        encoding="utf-8",
    )

    root = Path(__file__).resolve().parents[2]
    report = run_extraction(
        case_id="LK-TEST-0002",
        case_root=case_root,
        schema_root=root / "engine/schemas",
    )

    assert report["status"] == "COMPLETE_WITH_MODEL_REVIEW_REQUIRED"
    assert (case_root / "output/01-metadata/metadata.json").exists()
    assert (case_root / "output/05-evidence/evidence.json").exists()
