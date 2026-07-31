from pathlib import Path

import pytest

from legalkural.cli import ARTIFACTS, initialise_case, sha256


def test_sha256(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    source.write_bytes(b"%PDF-test")

    assert len(sha256(source)) == 64


def test_initialise_case(tmp_path: Path) -> None:
    source = tmp_path / "judgment.pdf"
    source.write_bytes(b"%PDF-test")

    case_root = initialise_case(
        input_pdf=source,
        output_root=tmp_path / "generated",
        case_id="LK-TEST-0001",
        overwrite=False,
    )

    assert (case_root / "manifest.json").exists()
    assert (case_root / "input/judgment.pdf").exists()
    assert (case_root / "evidence/source-integrity.txt").exists()

    for directory, filename in ARTIFACTS:
        assert (case_root / "output" / directory / filename).exists()


def test_rejects_missing_pdf(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        initialise_case(
            input_pdf=tmp_path / "missing.pdf",
            output_root=tmp_path / "generated",
            case_id="LK-TEST-0002",
            overwrite=False,
        )
