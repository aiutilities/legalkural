from pathlib import Path

from publishing.wordpress_featured_image import (
    prepare_featured_image,
)
from publishing.wordpress_media import MediaAsset


def test_ai_prompt_is_recommended_when_empty() -> None:
    result = prepare_featured_image(
        "Use Reveals the Truth",
        "The court examined actual use over formal labels.",
        MediaAsset(
            mode="ai",
            prompt="",
        ),
    )

    assert result["mode"] == "ai"
    assert "Use Reveals the Truth" in result["prompt"]


def test_editor_prompt_is_preserved() -> None:
    result = prepare_featured_image(
        "Title",
        "Excerpt",
        MediaAsset(
            mode="ai",
            prompt="A balanced scale above a house.",
        ),
    )

    assert result["prompt"] == (
        "A balanced scale above a house."
    )


def test_manual_upload() -> None:
    result = prepare_featured_image(
        "Title",
        "Excerpt",
        MediaAsset(
            mode="upload",
            path=Path("article.jpg"),
            caption="Caption",
            alt_text="A legal illustration",
            description="Editorial image",
        ),
    )

    assert result["mode"] == "upload"
    assert result["path"] == "article.jpg"
    assert result["caption"] == "Caption"


def test_publish_without_image() -> None:
    result = prepare_featured_image(
        "Title",
        "Excerpt",
        MediaAsset(mode="none"),
    )

    assert result["mode"] == "none"
    assert result["prompt"] is None
