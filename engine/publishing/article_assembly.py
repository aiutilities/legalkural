from __future__ import annotations

import html
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    title: str
    pdf_url: str
    qr_image_url: str


def render_inline_markdown(value: str) -> str:
    """Render the supported inline Markdown subset safely."""

    normalized = re.sub(
        r"\\([\\`*{}\[\]()#+\-.!_>])",
        r"\1",
        value.strip(),
    )

    rendered = html.escape(normalized, quote=True)

    rendered = re.sub(
        r"`([^`\n]+)`",
        r"<code>\1</code>",
        rendered,
    )
    rendered = re.sub(
        r"\*\*([^*\n]+)\*\*",
        r"<strong>\1</strong>",
        rendered,
    )
    rendered = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"<em>\1</em>",
        rendered,
    )

    return rendered


def markdown_to_html(
    markdown: str,
    *,
    drop_first_h1: bool = False,
) -> str:
    """Convert LegalKural's supported Markdown profile to safe HTML.

    Supported blocks:
    headings, paragraphs, ordered lists, unordered lists and
    blockquotes. Raw HTML is escaped. The conversion is deterministic
    and intentionally rejects unsupported fenced code and tables.
    """

    if not isinstance(markdown, str) or not markdown.strip():
        raise ValueError("Markdown article must be non-empty.")

    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    output: list[str] = []
    paragraph: list[str] = []
    active_list: str | None = None
    first_heading_seen = False

    def flush_paragraph() -> None:
        if not paragraph:
            return

        text = " ".join(
            item.strip()
            for item in paragraph
            if item.strip()
        )

        if text:
            output.append(
                f"<p>{render_inline_markdown(text)}</p>"
            )

        paragraph.clear()

    def close_list() -> None:
        nonlocal active_list

        if active_list is not None:
            output.append(f"</{active_list}>")
            active_list = None

    for raw_line in lines:
        stripped = raw_line.strip()

        if not stripped:
            flush_paragraph()
            close_list()
            continue

        if stripped.startswith("```"):
            raise ValueError(
                "Fenced code blocks are not supported."
            )

        if re.match(r"^\|.*\|$", stripped):
            raise ValueError(
                "Markdown tables are not supported."
            )

        heading = re.match(
            r"^(#{1,6})\s+(.+)$",
            stripped,
        )

        if heading:
            flush_paragraph()
            close_list()

            level = len(heading.group(1))
            text = heading.group(2).strip()

            should_drop = (
                drop_first_h1
                and not first_heading_seen
                and level == 1
            )

            first_heading_seen = True

            if not should_drop:
                output.append(
                    f"<h{level}>"
                    f"{render_inline_markdown(text)}"
                    f"</h{level}>"
                )

            continue

        first_heading_seen = True

        unordered = re.match(
            r"^[-*+]\s+(.+)$",
            stripped,
        )

        ordered = re.match(
            r"^(\d+)[.)]\s+(.+)$",
            stripped,
        )

        if unordered or ordered:
            flush_paragraph()

            list_type = "ul" if unordered else "ol"
            match = unordered or ordered
            assert match is not None

            if active_list != list_type:
                close_list()

                if ordered:
                    start = int(ordered.group(1))

                    if start == 1:
                        output.append("<ol>")
                    else:
                        output.append(
                            f'<ol start="{start}">'
                        )
                else:
                    output.append("<ul>")

                active_list = list_type

            item_text = (
                unordered.group(1)
                if unordered
                else ordered.group(2)
            )

            output.append(
                "<li>"
                + render_inline_markdown(item_text)
                + "</li>"
            )
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            close_list()

            quote = stripped[1:].strip()

            output.append(
                "<blockquote><p>"
                + render_inline_markdown(quote)
                + "</p></blockquote>"
            )
            continue

        close_list()
        paragraph.append(stripped)

    flush_paragraph()
    close_list()

    rendered = "\n".join(output).strip()

    if not rendered:
        raise ValueError(
            "Markdown conversion produced empty HTML."
        )

    return rendered + "\n"


def qr_download_block(doc: SourceDocument) -> str:
    title = html.escape(doc.title, quote=True)
    pdf_url = html.escape(doc.pdf_url, quote=True)
    qr_url = html.escape(doc.qr_image_url, quote=True)

    return (
        "<section class='lk-source-document'>"
        "<h3>Source Document</h3>"
        "<p>Scan the QR code in the journal or use the PDF link.</p>"
        f"<p><strong>{title}</strong></p>"
        f"<img src='{qr_url}' "
        "alt='QR Code for source document download' />"
        f"<p><a href='{pdf_url}'>Download PDF</a></p>"
        "</section>"
    )


def assemble_article(
    body_html: str,
    doc: SourceDocument | None,
) -> str:
    if doc is None:
        return body_html

    return body_html + "\n\n" + qr_download_block(doc)
