from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .article_assembly import (
    SourceDocument,
    assemble_article,
)
from .wordpress_author_resolver import (
    WordPressAuthorResolver,
)
from .wordpress_category_resolver import (
    WordPressCategoryResolver,
)
from .wordpress_idempotency import (
    IdempotentWordPressPublisher,
    publication_fingerprint,
)
from .wordpress_media import MediaAsset
from .wordpress_media_upload import WordPressMediaUploader
from .wordpress_metadata import LegalKuralMetadata
from .wordpress_models import (
    ContentType,
    PublishMode,
    WordPressPostRequest,
)
from .wordpress_publish import (
    validate_schedule,
    wordpress_status,
)
from .wordpress_tag_resolver import WordPressTagResolver


@dataclass(frozen=True)
class PipelineInput:
    title: str
    body_html: str
    excerpt: str
    slug: str
    content_type: ContentType
    category: str
    tags: list[str]
    author: str = "admin"
    publish_mode: PublishMode = PublishMode.DRAFT
    scheduled_at: datetime | None = None
    source_document: SourceDocument | None = None
    source_document_id: str | None = None
    featured_image: MediaAsset = MediaAsset(mode="none")


@dataclass(frozen=True)
class PipelineResult:
    action: str
    post_id: int
    status: str
    slug: str
    link: str | None
    payload: dict[str, Any]


class WordPressPublishingPipeline:
    def __init__(
        self,
        *,
        category_resolver: WordPressCategoryResolver,
        tag_resolver: WordPressTagResolver,
        author_resolver: WordPressAuthorResolver,
        publisher: IdempotentWordPressPublisher,
        media_uploader: WordPressMediaUploader | None = None,
    ) -> None:
        self.category_resolver = category_resolver
        self.tag_resolver = tag_resolver
        self.author_resolver = author_resolver
        self.publisher = publisher
        self.media_uploader = media_uploader

    def build_payload(
        self,
        item: PipelineInput,
    ) -> dict[str, Any]:
        validate_schedule(
            item.publish_mode,
            item.scheduled_at,
        )

        category_id = self.category_resolver.resolve(
            item.category
        )
        tag_ids = self.tag_resolver.resolve_many(
            item.tags
        )
        author_id = self.author_resolver.resolve(
            item.author
        )

        featured_media_id: int | None = None

        if item.featured_image.mode != "none":
            if self.media_uploader is None:
                raise RuntimeError(
                    "Media uploader is required for image mode."
                )

            if item.featured_image.path is None:
                raise ValueError(
                    "Generated or uploaded image requires a file path."
                )

            upload = self.media_uploader.upload(
                item.featured_image.path,
                title=item.title,
                caption=item.featured_image.caption,
                alt_text=item.featured_image.alt_text,
                description=item.featured_image.description,
            )
            featured_media_id = upload.media_id

        article_html = assemble_article(
            item.body_html,
            item.source_document,
        )

        metadata = LegalKuralMetadata(
            content_type=item.content_type,
            source_document_id=item.source_document_id,
            source_document_url=(
                item.source_document.pdf_url
                if item.source_document is not None
                else None
            ),
            qr_available=(
                item.source_document is not None
            ),
        ).to_wordpress_meta()

        request = WordPressPostRequest(
            title=item.title,
            content=article_html,
            excerpt=item.excerpt,
            slug=item.slug,
            content_type=item.content_type,
            category_ids=(category_id,),
            tag_ids=tuple(tag_ids),
            author_id=author_id,
            featured_media_id=featured_media_id,
            scheduled_at=item.scheduled_at,
            meta=metadata,
        )

        payload = request.to_payload()
        payload["status"] = wordpress_status(
            item.publish_mode
        )
        return payload

    def run(
        self,
        item: PipelineInput,
    ) -> PipelineResult:
        payload = self.build_payload(item)

        fingerprint = publication_fingerprint(
            slug=item.slug,
            title=item.title,
            content=payload["content"],
            excerpt=item.excerpt,
        )

        action, response = (
            self.publisher.create_or_update(
                slug=item.slug,
                payload=payload,
                fingerprint=fingerprint,
            )
        )

        post_id = response.get("id")
        status = response.get("status")
        slug = response.get("slug")
        link = response.get("link")

        if not isinstance(post_id, int):
            raise RuntimeError(
                "WordPress response is missing integer id."
            )

        if not isinstance(status, str):
            raise RuntimeError(
                "WordPress response is missing status."
            )

        if not isinstance(slug, str):
            raise RuntimeError(
                "WordPress response is missing slug."
            )

        return PipelineResult(
            action=action,
            post_id=post_id,
            status=status,
            slug=slug,
            link=link if isinstance(link, str) else None,
            payload=payload,
        )
