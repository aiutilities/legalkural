from pathlib import Path

from publishing.wordpress_client import HttpResponse
from publishing.wordpress_media_upload import (
    WordPressMediaUploader,
)
from publishing.wordpress_models import WordPressConfig


def test_media_upload(tmp_path: Path) -> None:
    image = tmp_path / "image.jpg"
    image.write_bytes(b"jpeg-data")
    calls = 0

    def transport(request, _timeout):
        nonlocal calls
        calls += 1

        if calls == 1:
            return HttpResponse(
                201,
                {},
                b'{"id": 88, "source_url": '
                b'"https://example.com/image.jpg"}',
            )

        return HttpResponse(
            200,
            {},
            b'{"id": 88}',
        )

    uploader = WordPressMediaUploader(
        WordPressConfig(
            site_url="https://example.com",
            username="admin",
            application_password="secret",
        ),
        transport=transport,
    )

    result = uploader.upload(
        image,
        title="Image",
        alt_text="Legal illustration",
    )

    assert result.media_id == 88
    assert calls == 2
