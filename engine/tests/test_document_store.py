from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfWriter

from publishing.document_store import (
    DocumentStore,
    DocumentStoreError,
)


def create_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as handle:
        writer.write(handle)


def create_package(
    root: Path,
    document_id: str = "DOC-TEST001",
) -> Path:
    package = root / document_id
    pdf_path = package / "public" / "judgment.pdf"
    create_pdf(pdf_path)

    payload = {
        "document_id": document_id,
        "published_filename": "judgment.pdf",
        "pdf_path": str(pdf_path),
        "title": "Judgment",
        "document_type": "JUDGMENT",
        "sha256": "a" * 64,
        "approval_status": "DRAFT",
    }

    (package / "document.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    return package


def test_register_approve_publish_resolve(
    tmp_path: Path,
) -> None:
    store = DocumentStore(tmp_path / "store")
    package = create_package(tmp_path)

    registered = store.register_package(package)
    assert registered["approval_status"] == "DRAFT"

    approved = store.approve("DOC-TEST001")
    assert approved["approval_status"] == "APPROVED"

    published = store.publish("DOC-TEST001")
    assert published["approval_status"] == "PUBLISHED"

    resolved = store.resolve(
        "DOC-TEST001",
        "judgment.pdf",
    )

    assert resolved.public_path.exists()
    assert resolved.download_path == (
        "/documents/DOC-TEST001/judgment.pdf"
    )


def test_unapproved_document_cannot_publish(
    tmp_path: Path,
) -> None:
    store = DocumentStore(tmp_path / "store")
    package = create_package(tmp_path)
    store.register_package(package)

    with pytest.raises(
        DocumentStoreError,
        match="approved",
    ):
        store.publish("DOC-TEST001")


def test_unpublished_document_cannot_resolve(
    tmp_path: Path,
) -> None:
    store = DocumentStore(tmp_path / "store")
    package = create_package(tmp_path)
    store.register_package(package)

    with pytest.raises(
        DocumentStoreError,
        match="not publicly available",
    ):
        store.resolve(
            "DOC-TEST001",
            "judgment.pdf",
        )


def test_withdraw_blocks_download(
    tmp_path: Path,
) -> None:
    store = DocumentStore(tmp_path / "store")
    package = create_package(tmp_path)

    store.register_package(package)
    store.approve("DOC-TEST001")
    store.publish("DOC-TEST001")
    store.withdraw("DOC-TEST001")

    with pytest.raises(
        DocumentStoreError,
        match="not publicly available",
    ):
        store.resolve(
            "DOC-TEST001",
            "judgment.pdf",
        )


def test_checksum_conflict_rejected(
    tmp_path: Path,
) -> None:
    store = DocumentStore(tmp_path / "store")
    first = create_package(tmp_path)
    store.register_package(first)

    payload_path = first / "document.json"
    payload = json.loads(
        payload_path.read_text(encoding="utf-8")
    )
    payload["sha256"] = "b" * 64
    payload_path.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    with pytest.raises(
        DocumentStoreError,
        match="different checksum",
    ):
        store.register_package(first)
