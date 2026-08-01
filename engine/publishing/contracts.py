from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_ROOT = ROOT / "engine" / "schemas"
CATEGORY_MASTER = ROOT / "engine" / "config" / "wordpress_categories.json"


class PublishingContractError(ValueError):
    pass


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_schema(payload: dict[str, Any], schema_name: str) -> None:
    validator = Draft202012Validator(
        _read(SCHEMA_ROOT / schema_name),
        format_checker=FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(payload),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        rendered = []
        for error in errors:
            location = ".".join(str(x) for x in error.absolute_path) or "<root>"
            rendered.append(f"{location}: {error.message}")
        raise PublishingContractError("Schema validation failed: " + " | ".join(rendered))


def categories() -> list[str]:
    payload = _read(CATEGORY_MASTER)

    validate_schema(
        payload,
        "wordpress_category_master.schema.json",
    )

    if payload.get("status") != "FROZEN":
        raise PublishingContractError(
            "WordPress category master is not frozen."
        )

    values = payload.get("categories")

    if not isinstance(values, list) or not values:
        raise PublishingContractError(
            "WordPress category master is empty."
        )

    return [str(item) for item in values]


def validate_tags(tags: list[str]) -> None:
    if not 5 <= len(tags) <= 9:
        raise PublishingContractError("Tags must contain between 5 and 9 entries.")
    normalized = [tag.strip().lower() for tag in tags]
    if len(normalized) != len(set(normalized)):
        raise PublishingContractError("Duplicate tags are not allowed.")
    for tag in tags:
        if not tag.strip() or re.search(r"\s", tag.strip()):
            raise PublishingContractError(f"Tag must be a non-empty single word: {tag}")


def validate_schedule(publication: dict[str, Any]) -> None:
    if publication["mode"] != "SCHEDULE":
        return
    raw = publication.get("scheduled_at")
    if not raw:
        raise PublishingContractError("Scheduled publication requires scheduled_at.")
    scheduled = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=ZoneInfo(publication["timezone"]))
    if scheduled.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise PublishingContractError("Scheduled publication must be in the future.")


def validate_image(image: dict[str, Any], mode: str) -> None:
    if image["mode"] == "NONE":
        if image.get("asset_id") is not None:
            raise PublishingContractError("No-image mode must not have asset_id.")
        return
    if not image.get("asset_id"):
        raise PublishingContractError("Image mode requires asset_id.")
    if mode != "DRAFT" and image.get("approval_status") != "APPROVED":
        raise PublishingContractError("Featured image must be approved before publication.")


def validate_wordpress_post(payload: dict[str, Any]) -> None:
    validate_schema(payload, "wordpress_post.schema.json")
    validate_tags(payload["tags"])
    if payload["category"] not in categories():
        raise PublishingContractError("Category must be selected from the frozen master.")
    validate_schedule(payload["publication"])
    validate_image(payload["featured_image"], payload["publication"]["mode"])
