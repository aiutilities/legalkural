from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DocumentStoreError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise DocumentStoreError(f"Metadata file not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


@dataclass(frozen=True)
class PublishedDocument:
    document_id: str
    filename: str
    public_path: Path
    download_path: str
    approval_status: str


class DocumentStore:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.registry_path = self.root / "registry.json"
        self.root.mkdir(parents=True, exist_ok=True)

        if not self.registry_path.exists():
            write_json(
                self.registry_path,
                {
                    "schema_version": "1.0",
                    "documents": {},
                    "updated_at": utc_now(),
                },
            )

    def _registry(self) -> dict[str, Any]:
        return read_json(self.registry_path)

    def _save_registry(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = utc_now()
        write_json(self.registry_path, payload)

    def register_package(self, package_root: Path) -> dict[str, Any]:
        package_root = package_root.expanduser().resolve()
        metadata_path = package_root / "document.json"
        metadata = read_json(metadata_path)

        document_id = metadata["document_id"]
        pdf_path = Path(metadata["pdf_path"]).expanduser().resolve()

        if not pdf_path.exists():
            raise DocumentStoreError(
                f"Published PDF does not exist: {pdf_path}"
            )

        filename = metadata["published_filename"]

        if not filename or not filename.endswith(".pdf"):
            raise DocumentStoreError(
                "Published filename must be a PDF."
            )

        destination = self.root / "documents" / document_id / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_path, destination)

        registry = self._registry()
        documents = registry.setdefault("documents", {})

        existing = documents.get(document_id)

        if existing and existing.get("sha256") != metadata.get("sha256"):
            raise DocumentStoreError(
                "Document ID already exists with a different checksum."
            )

        documents[document_id] = {
            "document_id": document_id,
            "filename": filename,
            "title": metadata["title"],
            "document_type": metadata["document_type"],
            "sha256": metadata["sha256"],
            "approval_status": metadata["approval_status"],
            "public_path": str(destination),
            "registered_at": utc_now(),
            "published_at": None,
            "withdrawn_at": None,
        }

        self._save_registry(registry)
        return documents[document_id]

    def approve(self, document_id: str) -> dict[str, Any]:
        registry = self._registry()
        documents = registry["documents"]

        if document_id not in documents:
            raise DocumentStoreError(
                f"Unknown document: {document_id}"
            )

        document = documents[document_id]
        document["approval_status"] = "APPROVED"
        document["approved_at"] = utc_now()

        self._save_registry(registry)
        return document

    def publish(self, document_id: str) -> dict[str, Any]:
        registry = self._registry()
        documents = registry["documents"]

        if document_id not in documents:
            raise DocumentStoreError(
                f"Unknown document: {document_id}"
            )

        document = documents[document_id]

        if document["approval_status"] != "APPROVED":
            raise DocumentStoreError(
                "Document must be approved before publication."
            )

        document["approval_status"] = "PUBLISHED"
        document["published_at"] = utc_now()

        self._save_registry(registry)
        return document

    def withdraw(self, document_id: str) -> dict[str, Any]:
        registry = self._registry()
        documents = registry["documents"]

        if document_id not in documents:
            raise DocumentStoreError(
                f"Unknown document: {document_id}"
            )

        document = documents[document_id]
        document["approval_status"] = "WITHDRAWN"
        document["withdrawn_at"] = utc_now()

        self._save_registry(registry)
        return document

    def resolve(
        self,
        document_id: str,
        filename: str,
    ) -> PublishedDocument:
        registry = self._registry()
        document = registry["documents"].get(document_id)

        if not document:
            raise DocumentStoreError("Document not found.")

        if document["approval_status"] != "PUBLISHED":
            raise DocumentStoreError(
                "Document is not publicly available."
            )

        if filename != document["filename"]:
            raise DocumentStoreError("Filename mismatch.")

        path = Path(document["public_path"])

        if not path.exists():
            raise DocumentStoreError(
                "Published document file is missing."
            )

        return PublishedDocument(
            document_id=document_id,
            filename=filename,
            public_path=path,
            download_path=f"/documents/{document_id}/{filename}",
            approval_status=document["approval_status"],
        )

    def list_documents(
        self,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        documents = list(
            self._registry()["documents"].values()
        )

        if status:
            documents = [
                item
                for item in documents
                if item["approval_status"] == status
            ]

        return sorted(
            documents,
            key=lambda item: item["registered_at"],
            reverse=True,
        )
