from pathlib import Path

from aidpl.extraction_worker import load_pages
from aidpl.law_worker import extract_law_map, run_law_analysis


def sample_source() -> str:
    return """<PAGE:1>
IN THE HIGH COURT OF JUDICATURE AT MADRAS
The petition is filed under Article 226 of the Constitution of India.
Section 100 of the Tamil Nadu Urban Local Bodies Act, 1998 provides an appeal.
Regulation 4(ii) of CMWSS Service Charges Regulations, 1998 was relied upon.
Notification No.12/2017-Central Tax (Rate) dated 28.06.2017 was considered.
The principles of natural justice were violated.
</PAGE:1>

<PAGE:2>
Collector of Central Excise v. Parle Exports (P) Ltd.,
[1989] 1 SCC 345 was considered.
In view of the above, this Court is of the considered view that
the premises must be classified according to actual use.
</PAGE:2>
"""


def test_extract_law_map(tmp_path: Path) -> None:
    source = tmp_path / "source-text.txt"
    source.write_text(sample_source(), encoding="utf-8")

    pages = load_pages(source)
    artifact = extract_law_map("LK-TEST-LAW-0001", pages)

    assert artifact["constitutional_provisions"]
    assert artifact["statutes"]
    assert artifact["regulations"]
    assert artifact["notifications"]
    assert artifact["legal_doctrines"]
    assert artifact["ratio_candidates"]


def test_run_law_analysis(tmp_path: Path) -> None:
    case_root = tmp_path / "case"
    working = case_root / "working"
    working.mkdir(parents=True)

    (working / "source-text.txt").write_text(
        sample_source(),
        encoding="utf-8",
    )

    root = Path(__file__).resolve().parents[2]

    report = run_law_analysis(
        case_id="LK-TEST-LAW-0002",
        case_root=case_root,
        schema_root=root / "engine/schemas",
    )

    assert report["schema_validation"] == "PASS"
    assert (case_root / "output/06-law/law.json").exists()
    assert (case_root / "evidence/law-analysis-report.json").exists()
