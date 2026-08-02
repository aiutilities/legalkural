from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from .wordpress_models import ContentType


@dataclass(frozen=True)
class LegalKuralMetadata:
    content_type: ContentType
    source_document_id: str | None = None
    source_document_url: str | None = None
    qr_available: bool = False
    journal_ready: bool = True
    algorithm_version: str = "1.0"
    publication_uuid: str | None = None

    def to_wordpress_meta(self) -> dict[str, Any]:
        publication_uuid = (
            self.publication_uuid or str(uuid.uuid4())
        )

        return {
            "legalkural_content_type": self.content_type.value,
            "legalkural_algorithm_version": (
                self.algorithm_version
            ),
            "legalkural_publication_uuid": publication_uuid,
            "legalkural_journal_ready": self.journal_ready,
            "legalkural_qr_available": self.qr_available,
            "legalkural_source_document_id": (
                self.source_document_id or ""
            ),
            "legalkural_source_document_url": (
                self.source_document_url or ""
            ),
        }
