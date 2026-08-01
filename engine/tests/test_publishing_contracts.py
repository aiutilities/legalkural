from datetime import datetime, timedelta, timezone

import pytest

from publishing.contracts import PublishingContractError, validate_wordpress_post


def base_post() -> dict:
    return {
        "schema_version": "1.0",
        "case_id": "LK-TEST-0001",
        "title": "Use Reveals the Truth",
        "slug": "use-reveals-the-truth",
        "excerpt": "A concise LegalKural account of how actual use can prevail over labels in law.",
        "category": "Property Law",
        "tags": ["property","tenant","housing","taxation","classification"],
        "author": {"id": "admin", "display_name": "Admin", "active": True},
        "publication": {"mode": "DRAFT", "timezone": "Asia/Kolkata", "scheduled_at": None},
        "featured_image": {"mode": "NONE", "asset_id": None, "approval_status": None},
        "source_documents": [],
        "status": "DRAFT"
    }


def test_valid_draft() -> None:
    validate_wordpress_post(base_post())


def test_tags_must_be_single_word() -> None:
    payload = base_post()
    payload["tags"][0] = "property law"
    with pytest.raises(PublishingContractError, match="single word"):
        validate_wordpress_post(payload)


def test_tags_must_be_between_five_and_nine() -> None:
    payload = base_post()
    payload["tags"] = ["one","two","three","four"]
    with pytest.raises(PublishingContractError):
        validate_wordpress_post(payload)


def test_category_must_come_from_master() -> None:
    payload = base_post()
    payload["category"] = "Invented"
    with pytest.raises(PublishingContractError, match="frozen master"):
        validate_wordpress_post(payload)


def test_schedule_must_be_future() -> None:
    payload = base_post()
    payload["publication"] = {
        "mode": "SCHEDULE",
        "timezone": "Asia/Kolkata",
        "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    }
    payload["status"] = "SCHEDULED"
    validate_wordpress_post(payload)


def test_publish_requires_approved_image_when_selected() -> None:
    payload = base_post()
    payload["publication"]["mode"] = "PUBLISH_NOW"
    payload["status"] = "PUBLISHED"
    payload["featured_image"] = {
        "mode": "UPLOAD",
        "asset_id": "IMG-001",
        "approval_status": "DRAFT"
    }
    with pytest.raises(PublishingContractError, match="approved"):
        validate_wordpress_post(payload)
