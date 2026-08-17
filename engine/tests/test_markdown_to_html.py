import pytest

from publishing.article_assembly import (
    markdown_to_html,
    render_inline_markdown,
)


def test_markdown_to_html_supported_profile() -> None:
    markdown = """# Article Title

## Case Snapshot

A **verified** paragraph with Tamil: பயன்பாடே பொருள்.

- Court: High Court
- Result: Allowed

1) First reason
2) Second reason

> This is not legal advice.
"""

    rendered = markdown_to_html(
        markdown,
        drop_first_h1=True,
    )

    assert "<h1>" not in rendered
    assert "<h2>Case Snapshot</h2>" in rendered
    assert "<strong>verified</strong>" in rendered
    assert "பயன்பாடே பொருள்" in rendered
    assert "<ul>" in rendered
    assert "<li>Court: High Court</li>" in rendered
    assert "<ol>" in rendered
    assert "<li>First reason</li>" in rendered
    assert (
        "<blockquote><p>This is not legal advice."
        "</p></blockquote>"
    ) in rendered


def test_markdown_to_html_escapes_raw_html() -> None:
    rendered = markdown_to_html(
        "# Title\n\n<script>alert('x')</script>"
    )

    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_render_inline_markdown_escapes_attributes() -> None:
    rendered = render_inline_markdown(
        '**"quoted" & verified**'
    )

    assert rendered == (
        "<strong>&quot;quoted&quot; &amp; verified</strong>"
    )


def test_markdown_to_html_is_deterministic() -> None:
    source = "# Title\n\n- One\n- Two\n"

    first = markdown_to_html(
        source,
        drop_first_h1=True,
    )
    second = markdown_to_html(
        source,
        drop_first_h1=True,
    )

    assert first == second


@pytest.mark.parametrize(
    "source, message",
    [
        ("# Title\n\n```python\npass\n```", "Fenced code"),
        ("# Title\n\n| A | B |", "tables"),
    ],
)
def test_markdown_to_html_rejects_unsupported_blocks(
    source: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        markdown_to_html(source)

def test_markdown_to_html_preserves_explicit_ordered_numbers() -> None:
    rendered = markdown_to_html(
        """# Title

1) First question

2) Second question

7) Seventh reason
""",
        drop_first_h1=True,
    )

    assert "<ol>" in rendered
    assert '<ol start="2">' in rendered
    assert '<ol start="7">' in rendered
    assert "<li>First question</li>" in rendered
    assert "<li>Second question</li>" in rendered
    assert "<li>Seventh reason</li>" in rendered


def test_inline_markdown_removes_supported_escape_sequences() -> None:
    rendered = render_inline_markdown(
        r"W\.P.Nos.10194 and escaped \- punctuation"
    )

    assert rendered == (
        "W.P.Nos.10194 and escaped - punctuation"
    )
    assert "\\" not in rendered
