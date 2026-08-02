from __future__ import annotations

from publishing.wordpress_metadata import LegalKuralMetadata
from publishing.wordpress_models import ContentType


def test_metadata_serialization() -> None:
    metadata = LegalKuralMetadata(
        content_type=ContentType.JUDGMENT,
        source_document_id="DOC-001",
        source_document_url="https://example.com/doc.pdf",
        qr_available=True,
        publication_uuid="PUB-001",
    )

    payload = metadata.to_wordpress_meta()

    assert payload["legalkural_content_type"] == "Judgment"
    assert payload["legalkural_publication_uuid"] == "PUB-001"
    assert payload["legalkural_qr_available"] is True
    assert payload["legalkural_source_document_id"] == "DOC-001"
