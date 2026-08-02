from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

from .article_assembly import SourceDocument
from .wordpress_author_resolver import (
    WordPressAuthorResolver,
)
from .wordpress_category_resolver import (
    WordPressCategoryResolver,
)
from .wordpress_client import WordPressClient
from .wordpress_idempotency import (
    IdempotentWordPressPublisher,
    PublicationRegistry,
)
from .wordpress_media import MediaAsset
from .wordpress_media_upload import WordPressMediaUploader
from .wordpress_models import (
    ContentType,
    PublishMode,
    WordPressConfig,
)
from .wordpress_pipeline import (
    PipelineInput,
    WordPressPublishingPipeline,
)
from .wordpress_tag_resolver import WordPressTagResolver


def config_from_environment() -> WordPressConfig:
    return WordPressConfig(
        site_url=os.environ.get("WORDPRESS_SITE_URL", ""),
        username=os.environ.get("WORDPRESS_USERNAME", ""),
        application_password=os.environ.get(
            "WORDPRESS_APPLICATION_PASSWORD",
            "",
        ),
        timeout_seconds=float(
            os.environ.get("WORDPRESS_TIMEOUT_SECONDS", "30")
        ),
        max_attempts=int(
            os.environ.get("WORDPRESS_MAX_ATTEMPTS", "3")
        ),
    )


def parse_input(payload: dict) -> PipelineInput:
    source = payload.get("source_document")
    document = None

    if source:
        document = SourceDocument(
            title=source["title"],
            pdf_url=source["pdf_url"],
            qr_image_url=source["qr_image_url"],
        )

    image = payload.get(
        "featured_image",
        {"mode": "none"},
    )

    scheduled_at = payload.get("scheduled_at")

    return PipelineInput(
        title=payload["title"],
        body_html=payload["body_html"],
        excerpt=payload["excerpt"],
        slug=payload["slug"],
        content_type=ContentType(
            payload["content_type"]
        ),
        category=payload["category"],
        tags=list(payload["tags"]),
        author=payload.get("author", "admin"),
        publish_mode=PublishMode(
            payload.get("publish_mode", "DRAFT")
        ),
        scheduled_at=(
            datetime.fromisoformat(scheduled_at)
            if scheduled_at
            else None
        ),
        source_document=document,
        source_document_id=payload.get(
            "source_document_id"
        ),
        featured_image=MediaAsset(
            mode=image.get("mode", "none"),
            path=(
                Path(image["path"])
                if image.get("path")
                else None
            ),
            caption=image.get("caption", ""),
            alt_text=image.get("alt_text", ""),
            description=image.get("description", ""),
        ),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="legalkural-wordpress-pipeline"
    )
    parser.add_argument("package", type=Path)
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(
            "generated/wordpress/publications.json"
        ),
    )
    parser.add_argument(
        "--allow-live",
        action="store_true",
    )
    args = parser.parse_args()

    if not args.allow_live:
        raise SystemExit(
            "ERROR: Live WordPress execution requires "
            "--allow-live."
        )

    payload = json.loads(
        args.package.read_text(encoding="utf-8")
    )
    item = parse_input(payload)

    config = config_from_environment()
    client = WordPressClient(config)

    pipeline = WordPressPublishingPipeline(
        category_resolver=WordPressCategoryResolver(
            client
        ),
        tag_resolver=WordPressTagResolver(client),
        author_resolver=WordPressAuthorResolver(
            client
        ),
        publisher=IdempotentWordPressPublisher(
            client,
            PublicationRegistry(args.registry),
        ),
        media_uploader=WordPressMediaUploader(config),
    )

    result = pipeline.run(item)

    print(
        json.dumps(
            {
                "action": result.action,
                "post_id": result.post_id,
                "status": result.status,
                "slug": result.slug,
                "link": result.link,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
