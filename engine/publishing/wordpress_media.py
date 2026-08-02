from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
}


@dataclass(frozen=True)
class MediaAsset:
    mode: str
    path: Path | None = None
    prompt: str | None = None
    caption: str = ""
    alt_text: str = ""
    description: str = ""


def validate_media(asset: MediaAsset) -> None:
    if asset.mode == "none":
        if asset.path is not None:
            raise ValueError(
                "No-image mode cannot include a file path."
            )
        return

    if asset.mode == "upload":
        if asset.path is None:
            raise ValueError(
                "Upload mode requires an image path."
            )

        if (
            asset.path.suffix.lower()
            not in SUPPORTED_EXTENSIONS
        ):
            raise ValueError(
                "Unsupported image format."
            )
        return

    if asset.mode == "ai":
        # Empty prompt is valid here because the prompt agent
        # may recommend one from the article title/excerpt.
        return

    raise ValueError("Unknown media mode.")
