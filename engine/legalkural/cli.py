from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ARTIFACTS = [
    ("01-metadata", "metadata.json"),
    ("02-timeline", "timeline.json"),
    ("03-facts", "facts.json"),
    ("04-issues", "issues.json"),
    ("05-evidence", "evidence.json"),
    ("06-law", "law.json"),
    ("07-reasoning", "reasoning.json"),
    ("08-decision", "decision.json"),
    ("09-kural", "kural.md"),
    ("10-article", "article.md"),
    ("11-learning", "thinking-review.md"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def require_pdf(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")

    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Input must be a PDF: {path}")

    if path.stat().st_size == 0:
        raise ValueError(f"Input PDF is empty: {path}")


def create_json_placeholder(path: Path, case_id: str, artifact: str) -> None:
    payload = {
        "schema_version": "1.0",
        "reference_case_id": case_id,
        "artifact": artifact,
        "status": "PENDING_GENERATION",
    }

    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def create_markdown_placeholder(path: Path, case_id: str, artifact: str) -> None:
    content = f"""# {artifact}

**Reference Case:** {case_id}

**Status:** Pending Generation
"""
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def initialise_case(
    input_pdf: Path,
    output_root: Path,
    case_id: str,
    overwrite: bool,
) -> Path:
    require_pdf(input_pdf)

    case_root = output_root / case_id
    input_dir = case_root / "input"
    output_dir = case_root / "output"
    evidence_dir = case_root / "evidence"

    if case_root.exists() and not overwrite:
        raise FileExistsError(
            f"Case output already exists: {case_root}. "
            "Use --overwrite to replace it."
        )

    if case_root.exists():
        shutil.rmtree(case_root)

    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    evidence_dir.mkdir(parents=True)

    stored_pdf = input_dir / "judgment.pdf"
    shutil.copy2(input_pdf, stored_pdf)

    digest = sha256(stored_pdf)
    generated_at = datetime.now(timezone.utc).isoformat()

    manifest = {
        "engine": "Legal Kural ThinkingOS Engine",
        "engine_version": "0.1.0",
        "case_id": case_id,
        "status": "INITIALISED",
        "generated_at_utc": generated_at,
        "input": {
            "original_file_name": input_pdf.name,
            "stored_path": str(stored_pdf),
            "size_bytes": stored_pdf.stat().st_size,
            "sha256": digest,
        },
        "artifacts": [],
    }

    for directory, filename in ARTIFACTS:
        artifact_dir = output_dir / directory
        artifact_dir.mkdir(parents=True)

        artifact_path = artifact_dir / filename

        if artifact_path.suffix == ".json":
            create_json_placeholder(artifact_path, case_id, directory)
        else:
            create_markdown_placeholder(artifact_path, case_id, directory)

        manifest["artifacts"].append(
            {
                "name": directory,
                "path": str(artifact_path),
                "status": "PENDING_GENERATION",
            }
        )

    manifest_path = case_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    integrity_path = evidence_dir / "source-integrity.txt"
    integrity_path.write_text(
        "\n".join(
            [
                f"Reference Case: {case_id}",
                f"Original File: {input_pdf.name}",
                f"Stored File: {stored_pdf}",
                f"SHA-256: {digest}",
                "Status: VERIFIED",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return case_root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legalkural",
        description=(
            "Initialise a Legal Kural ThinkingOS case package "
            "from a judgment PDF."
        ),
    )

    parser.add_argument(
        "input_pdf",
        type=Path,
        help="Path to the source judgment PDF.",
    )

    parser.add_argument(
        "--case-id",
        required=True,
        help="Stable case identifier, for example LK-REF-0002.",
    )

    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("generated"),
        help="Root directory for generated case packages.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing generated case package.",
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        case_root = initialise_case(
            input_pdf=args.input_pdf.expanduser().resolve(),
            output_root=args.output_root,
            case_id=args.case_id,
            overwrite=args.overwrite,
        )
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print()
    print("=" * 60)
    print("LEGAL KURAL THINKINGOS ENGINE")
    print("=" * 60)
    print(f"Case package : {case_root}")
    print(f"Manifest     : {case_root / 'manifest.json'}")
    print("Status       : INITIALISED")
    print("Artifacts    : 11")
    print("=" * 60)

    return 0
