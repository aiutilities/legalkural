from pathlib import Path

import pytest

from publishing.wordpress_media import (
    MediaAsset,
    validate_media,
)


def test_no_image_mode() -> None:
    validate_media(MediaAsset(mode="none"))


def test_upload_mode() -> None:
    validate_media(
        MediaAsset(
            mode="upload",
            path=Path("article.png"),
        )
    )


def test_ai_mode_allows_recommended_prompt() -> None:
    validate_media(
        MediaAsset(
            mode="ai",
            prompt="",
        )
    )


def test_upload_rejects_unsupported_format() -> None:
    with pytest.raises(
        ValueError,
        match="Unsupported",
    ):
        validate_media(
            MediaAsset(
                mode="upload",
                path=Path("article.bmp"),
            )
        )


def test_unknown_mode_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="Unknown",
    ):
        validate_media(
            MediaAsset(mode="other")
        )
