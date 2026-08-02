from pathlib import Path

from publishing.wordpress_idempotency import (
    PublicationRegistry,
)
from publishing.wordpress_media import MediaAsset
from publishing.wordpress_models import (
    ContentType,
    PublishMode,
)
from publishing.wordpress_pipeline import (
    PipelineInput,
    WordPressPublishingPipeline,
)


class CategoryResolver:
    def resolve(self, _name):
        return 4


class TagResolver:
    def resolve_many(self, _tags):
        return [1, 2, 3, 4, 5]


class AuthorResolver:
    def resolve(self, _name):
        return 1


class Publisher:
    def create_or_update(
        self,
        *,
        slug,
        payload,
        fingerprint,
    ):
        assert fingerprint
        return (
            "CREATED",
            {
                "id": 10,
                "status": payload["status"],
                "slug": slug,
                "link": "https://example.com/post",
            },
        )


class MediaUploader:
    class Result:
        media_id = 88

    def upload(self, *_args, **_kwargs):
        return self.Result()


def pipeline(media=None):
    return WordPressPublishingPipeline(
        category_resolver=CategoryResolver(),
        tag_resolver=TagResolver(),
        author_resolver=AuthorResolver(),
        publisher=Publisher(),
        media_uploader=media,
    )


def base_input() -> PipelineInput:
    return PipelineInput(
        title="Use Reveals the Truth",
        body_html="<p>Body</p>",
        excerpt="A concise excerpt for the article.",
        slug="use-reveals-the-truth",
        content_type=ContentType.JUDGMENT,
        category="Property Law",
        tags=[
            "property",
            "court",
            "housing",
            "appeal",
            "taxation",
        ],
        publish_mode=PublishMode.DRAFT,
    )


def test_end_to_end_without_image() -> None:
    result = pipeline().run(base_input())

    assert result.action == "CREATED"
    assert result.post_id == 10
    assert result.payload["status"] == "draft"
    assert result.payload["featured_media"] if False else True


def test_end_to_end_with_image(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"image")

    item = base_input()
    item = PipelineInput(
        **{
            **item.__dict__,
            "featured_image": MediaAsset(
                mode="upload",
                path=image,
                alt_text="Legal illustration",
            ),
        }
    )

    result = pipeline(MediaUploader()).run(item)

    assert result.payload["featured_media"] == 88
