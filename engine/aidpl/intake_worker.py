from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .orchestrator import (
    complete_agent,
    load_plan,
    save_plan,
    start_agent,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def verify_pdf(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input PDF does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Input must use the .pdf extension: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"Input PDF is empty: {path}")

    with path.open("rb") as handle:
        signature = handle.read(5)

    if signature != b"%PDF-":
        raise ValueError(f"Input does not have a valid PDF signature: {path}")


def normalize_text(text: str) -> str:
    lines = []

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        lines.append(raw_line.rstrip())

    normalized = "\n".join(lines)

    while "\n\n\n" in normalized:
        normalized = normalized.replace("\n\n\n", "\n\n")

    return normalized.strip()


def extract_pdf(path: Path) -> tuple[list[dict[str, Any]], str]:
    reader = PdfReader(str(path))

    if reader.is_encrypted:
        try:
            result = reader.decrypt("")
        except Exception as exc:
            raise ValueError("Encrypted PDF could not be opened.") from exc

        if result == 0:
            raise ValueError("Encrypted PDF requires a password.")

    pages: list[dict[str, Any]] = []
    combined_parts: list[str] = []

    for index, page in enumerate(reader.pages, start=1):
        extracted = page.extract_text() or ""
        normalized = normalize_text(extracted)

        pages.append(
            {
                "page": index,
                "characters": len(normalized),
                "text_available": bool(normalized),
            }
        )

        combined_parts.append(
            "\n".join(
                [
                    f"<PAGE:{index}>",
                    normalized,
                    f"</PAGE:{index}>",
                ]
            )
        )

    return pages, "\n\n".join(combined_parts).rstrip() + "\n"


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_manifest(
    case_root: Path,
    case_id: str,
    source_pdf: Path,
    stored_pdf: Path,
    digest: str,
    page_count: int,
    extracted_characters: int,
) -> None:
    manifest_path = case_root / "manifest.json"

    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "engine": "Legal Kural ThinkingOS Engine",
            "engine_version": "0.1.0",
            "case_id": case_id,
            "artifacts": [],
        }

    manifest["status"] = "INTAKE_COMPLETE"
    manifest["updated_at_utc"] = utc_now()
    manifest["input"] = {
        "original_file_name": source_pdf.name,
        "stored_path": str(stored_pdf),
        "size_bytes": stored_pdf.stat().st_size,
        "sha256": digest,
        "page_count": page_count,
        "extracted_characters": extracted_characters,
    }

    write_json(manifest_path, manifest)


def run_intake(
    source_pdf: Path,
    case_id: str,
    case_root: Path,
    overwrite: bool,
) -> dict[str, Any]:
    source_pdf = source_pdf.expanduser().resolve()
    case_root = case_root.expanduser().resolve()

    verify_pdf(source_pdf)

    input_dir = case_root / "input"
    working_dir = case_root / "working"
    evidence_dir = case_root / "evidence"

    input_dir.mkdir(parents=True, exist_ok=True)
    working_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    stored_pdf = input_dir / "judgment.pdf"

    if stored_pdf.exists() and not overwrite:
        if stored_pdf.resolve() != source_pdf:
            raise FileExistsError(
                f"Stored judgment already exists: {stored_pdf}. "
                "Use --overwrite to replace it."
            )
    elif stored_pdf.resolve() != source_pdf:
        shutil.copy2(source_pdf, stored_pdf)

    verify_pdf(stored_pdf)

    pages, source_text = extract_pdf(stored_pdf)
    digest = sha256(stored_pdf)
    extracted_characters = sum(page["characters"] for page in pages)
    pages_with_text = sum(1 for page in pages if page["text_available"])

    if not pages:
        raise ValueError("PDF contains no readable pages.")

    if extracted_characters == 0:
        raise ValueError(
            "No embedded text could be extracted. "
            "OCR support is required for this PDF."
        )

    text_path = working_dir / "source-text.txt"
    page_map_path = working_dir / "page-map.json"
    report_path = evidence_dir / "intake-report.json"
    integrity_json_path = evidence_dir / "source-integrity.json"
    integrity_text_path = evidence_dir / "source-integrity.txt"

    text_path.write_text(source_text, encoding="utf-8")
    write_json(page_map_path, pages)

    integrity = {
        "schema_version": "1.0",
        "case_id": case_id,
        "source_file": str(stored_pdf),
        "sha256": digest,
        "size_bytes": stored_pdf.stat().st_size,
        "pdf_signature_valid": True,
        "page_count": len(pages),
        "status": "VERIFIED",
        "verified_at_utc": utc_now(),
    }
    write_json(integrity_json_path, integrity)

    integrity_text_path.write_text(
        "\n".join(
            [
                f"Reference Case: {case_id}",
                f"Source File: {stored_pdf}",
                f"SHA-256: {digest}",
                f"Pages: {len(pages)}",
                "PDF Signature: VALID",
                "Status: VERIFIED",
                "",
            ]
        ),
        encoding="utf-8",
    )

    report = {
        "schema_version": "1.0",
        "agent_id": "LK-INTAKE",
        "case_id": case_id,
        "status": "COMPLETE",
        "completed_at_utc": utc_now(),
        "input": {
            "source_pdf": str(source_pdf),
            "stored_pdf": str(stored_pdf),
        },
        "validation": {
            "pdf_signature_valid": True,
            "sha256": digest,
            "page_count": len(pages),
            "pages_with_text": pages_with_text,
            "pages_without_text": len(pages) - pages_with_text,
            "extracted_characters": extracted_characters,
            "text_extraction": "PASS",
            "document_completeness": (
                "TEXT_PRESENT_ON_ALL_PAGES"
                if pages_with_text == len(pages)
                else "REVIEW_REQUIRED"
            ),
        },
        "outputs": [
            str(stored_pdf),
            str(text_path),
            str(page_map_path),
            str(integrity_json_path),
            str(integrity_text_path),
        ],
        "next_agent": "LK-EXTRACT",
    }
    write_json(report_path, report)

    update_manifest(
        case_root=case_root,
        case_id=case_id,
        source_pdf=source_pdf,
        stored_pdf=stored_pdf,
        digest=digest,
        page_count=len(pages),
        extracted_characters=extracted_characters,
    )

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aidpl-intake",
        description="Run the Legal Kural Judgment Intake Agent.",
    )

    parser.add_argument("source_pdf", type=Path)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--overwrite", action="store_true")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    plan = None

    try:
        if args.plan:
            plan = load_plan(args.plan)
            start_agent(plan, "LK-INTAKE")
            save_plan(args.plan, plan)

        report = run_intake(
            source_pdf=args.source_pdf,
            case_id=args.case_id,
            case_root=args.case_root,
            overwrite=args.overwrite,
        )

        if args.plan and plan is not None:
            plan = load_plan(args.plan)
            complete_agent(
                plan,
                "LK-INTAKE",
                reviewer="AI-CEO",
                note="Deterministic PDF intake validation passed.",
            )
            save_plan(args.plan, plan)

        print()
        print("=" * 72)
        print("LEGAL KURAL JUDGMENT INTAKE AGENT")
        print("=" * 72)
        print(f"Case        : {args.case_id}")
        print(f"Pages       : {report['validation']['page_count']}")
        print(
            "Characters  : "
            f"{report['validation']['extracted_characters']}"
        )
        print(f"SHA-256     : {report['validation']['sha256']}")
        print("Status      : COMPLETE")
        print("Next Agent  : LK-EXTRACT")
        print("=" * 72)
        return 0

    except (
        FileExistsError,
        FileNotFoundError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
