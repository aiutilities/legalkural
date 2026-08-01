from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import qrcode
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {
    ".pdf": "PDF",
    ".doc": "DOC",
    ".docx": "DOCX",
    ".xls": "XLS",
    ".xlsx": "XLSX",
    ".csv": "CSV",
}


class DocumentProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class DocumentResult:
    document_id: str
    original_path: Path
    pdf_path: Path
    qr_path: Path
    sha256: str
    page_count: int
    original_format: str
    conversion_status: str
    download_url: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered or "document"


def detect_format(path: Path) -> str:
    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentProcessingError(
            f"Unsupported document format: {extension or '<none>'}"
        )

    return SUPPORTED_EXTENSIONS[extension]


def validate_pdf(path: Path) -> int:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:
        raise DocumentProcessingError(
            f"Invalid PDF output: {exc}"
        ) from exc

    page_count = len(reader.pages)

    if page_count < 1:
        raise DocumentProcessingError(
            "PDF output contains no pages."
        )

    return page_count


def find_soffice() -> str:
    candidates = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return str(candidate)

    raise DocumentProcessingError(
        "LibreOffice conversion engine is not installed. "
        "Install LibreOffice before converting Word or spreadsheet files."
    )


def convert_to_pdf(
    source: Path,
    destination_dir: Path,
) -> tuple[Path, str]:
    source = source.expanduser().resolve()
    destination_dir.mkdir(parents=True, exist_ok=True)

    source_format = detect_format(source)

    if source_format == "PDF":
        destination = destination_dir / source.name
        shutil.copy2(source, destination)
        validate_pdf(destination)
        return destination, "NOT_REQUIRED"

    soffice = find_soffice()

    command = [
        soffice,
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(destination_dir),
        str(source),
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        raise DocumentProcessingError(
            "Document conversion failed: "
            + (completed.stderr.strip() or completed.stdout.strip())
        )

    output = destination_dir / f"{source.stem}.pdf"

    if not output.exists():
        candidates = sorted(destination_dir.glob("*.pdf"))
        if len(candidates) == 1:
            output = candidates[0]
        else:
            raise DocumentProcessingError(
                "Conversion completed without a discoverable PDF output."
            )

    validate_pdf(output)
    return output, "CONVERTED"


def generate_qr(
    url: str,
    output_path: Path,
) -> Path:
    if not (
        url.startswith("https://")
        or url.startswith("http://")
    ):
        raise DocumentProcessingError(
            "QR download URL must use HTTP or HTTPS."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    image = qrcode.make(url)
    image.save(output_path)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise DocumentProcessingError(
            "QR generation failed."
        )

    return output_path


def process_document(
    *,
    source: Path,
    output_root: Path,
    title: str,
    document_type: str,
    uploaded_by: str,
    download_base_url: str,
) -> tuple[DocumentResult, dict[str, Any]]:
    source = source.expanduser().resolve()

    if not source.exists() or not source.is_file():
        raise DocumentProcessingError(
            f"Source document not found: {source}"
        )

    document_id = f"DOC-{uuid.uuid4().hex[:12].upper()}"
    document_root = output_root.expanduser().resolve() / document_id
    original_dir = document_root / "original"
    public_dir = document_root / "public"
    qr_dir = document_root / "qr"

    original_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    qr_dir.mkdir(parents=True, exist_ok=True)

    original_copy = original_dir / source.name
    shutil.copy2(source, original_copy)

    original_format = detect_format(original_copy)
    raw_pdf_path, conversion_status = convert_to_pdf(
        original_copy,
        public_dir,
    )

    published_filename = f"{slugify(title)}.pdf"
    published_pdf = public_dir / published_filename

    if raw_pdf_path != published_pdf:
        if published_pdf.exists():
            published_pdf.unlink()
        raw_pdf_path.rename(published_pdf)

    page_count = validate_pdf(published_pdf)
    checksum = sha256_file(original_copy)

    download_url = (
        download_base_url.rstrip("/")
        + "/"
        + document_id
        + "/"
        + published_filename
    )

    qr_path = generate_qr(
        download_url,
        qr_dir / f"{document_id.lower()}-qr.png",
    )

    result = DocumentResult(
        document_id=document_id,
        original_path=original_copy,
        pdf_path=published_pdf,
        qr_path=qr_path,
        sha256=checksum,
        page_count=page_count,
        original_format=original_format,
        conversion_status=conversion_status,
        download_url=download_url,
    )

    payload = {
        "schema_version": "1.0",
        "document_id": document_id,
        "document_type": document_type,
        "title": title,
        "original_filename": source.name,
        "published_filename": published_filename,
        "original_format": original_format,
        "conversion_status": conversion_status,
        "approval_status": "DRAFT",
        "source_authority": None,
        "document_date": None,
        "sha256": checksum,
        "uploaded_by": uploaded_by,
        "uploaded_at": utc_now(),
        "pdf_path": str(published_pdf),
        "download_url": download_url,
        "qr_path": str(qr_path),
        "page_count": page_count,
    }

    metadata_path = document_root / "document.json"
    metadata_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return result, payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="legalkural-document",
        description=(
            "Preserve a source document, convert its public copy to PDF, "
            "and generate a QR code."
        ),
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--document-type",
        required=True,
        choices=[
            "JUDGMENT",
            "GOVERNMENT_ORDER",
            "CIRCULAR",
            "REPORT",
            "ANNEXURE",
            "SPREADSHEET",
            "OTHER",
        ],
    )
    parser.add_argument("--uploaded-by", default="admin")
    parser.add_argument("--download-base-url", required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        result, _ = process_document(
            source=args.source,
            output_root=args.output_root,
            title=args.title,
            document_type=args.document_type,
            uploaded_by=args.uploaded_by,
            download_base_url=args.download_base_url,
        )
    except DocumentProcessingError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("=" * 72)
    print("LEGALKURAL DOCUMENT CONVERSION + QR")
    print("=" * 72)
    print(f"Document ID : {result.document_id}")
    print(f"Format      : {result.original_format}")
    print(f"Conversion  : {result.conversion_status}")
    print(f"Pages       : {result.page_count}")
    print(f"PDF         : {result.pdf_path}")
    print(f"QR          : {result.qr_path}")
    print(f"URL         : {result.download_url}")
    print("=" * 72)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
