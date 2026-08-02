from __future__ import annotations

from typing import Any

from .wordpress_image_prompt import recommend_prompt
from .wordpress_media import MediaAsset, validate_media


def prepare_featured_image(
    title: str,
    excerpt: str,
    asset: MediaAsset,
) -> dict[str, Any]:
    validate_media(asset)

    if asset.mode == "none":
        return {
            "mode": "none",
            "prompt": None,
            "caption": "",
            "alt": "",
            "description": "",
        }

    prompt = (
        asset.prompt.strip()
        if asset.prompt and asset.prompt.strip()
        else recommend_prompt(title, excerpt)
    )

    return {
        "mode": asset.mode,
        "path": (
            str(asset.path)
            if asset.path is not None
            else None
        ),
        "prompt": prompt,
        "caption": asset.caption,
        "alt": asset.alt_text,
        "description": asset.description,
    }
