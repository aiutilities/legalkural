"""Minimal deterministic English PDF renderer for LegalKural journals."""

from __future__ import annotations

from html.parser import HTMLParser
import hashlib
from pathlib import Path
import re
import textwrap
from typing import Any

from pypdf import PdfReader
import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

from .assembly import validate_assembly


RENDERER_VERSION = "1.0.0"
TAMIL_PATTERN = re.compile(r"[\u0B80-\u0BFF]")
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6"}

PUNCTUATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
)


class JournalRenderError(ValueError):
    """Raised when a journal cannot be rendered safely."""


FONT_REGULAR = "LegalKuralSans"
FONT_BOLD = "LegalKuralSans-Bold"
FONT_ITALIC = "LegalKuralSans-Italic"


def _register_embedded_fonts() -> None:
    font_root = Path(reportlab.__file__).resolve().parent / "fonts"
    files = {
        FONT_REGULAR: font_root / "Vera.ttf",
        FONT_BOLD: font_root / "VeraBd.ttf",
        FONT_ITALIC: font_root / "VeraIt.ttf",
    }

    for font_name, font_path in files.items():
        if not font_path.is_file():
            raise JournalRenderError(
                f"bundled ReportLab font is missing: {font_path}"
            )

        if font_name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(font_name, str(font_path))
            )


class _BlockParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._tag: str | None = None
        self._parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized = tag.lower()

        if normalized in {"script", "style"}:
            self._ignored_depth += 1
            return

        if self._ignored_depth:
            return

        if normalized in BLOCK_TAGS:
            self._flush()
            self._tag = normalized
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()

        if normalized in {"script", "style"}:
            self._ignored_depth = max(0, self._ignored_depth - 1)
            return

        if self._ignored_depth:
            return

        if normalized == self._tag:
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and self._tag is not None:
            self._parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush()

    def _flush(self) -> None:
        if self._tag is None:
            return

        text = " ".join("".join(self._parts).split())
        if text:
            self.blocks.append((self._tag, text))

        self._tag = None
        self._parts = []


def _latin_text(value: str) -> str:
    normalized = value.translate(PUNCTUATION)
    return normalized.encode("latin-1", errors="replace").decode("latin-1")


def extract_english_article_blocks(
    content_html: str,
) -> list[tuple[str, str]]:
    """Extract substantive English blocks, excluding the Kural preamble."""

    parser = _BlockParser()
    parser.feed(content_html)
    parser.close()

    blocks = [
        (tag, _latin_text(text))
        for tag, text in parser.blocks
        if not TAMIL_PATTERN.search(text)
    ]

    # The certified WordPress article places the editorial/Kural preamble
    # before the first substantive H2 section. The journal uses only the
    # algorithm-derived article title, so that preamble is excluded.
    first_h2 = next(
        (index for index, (tag, _) in enumerate(blocks) if tag == "h2"),
        None,
    )
    if first_h2 is not None:
        blocks = blocks[first_h2:]

    return blocks


def _wrapped_lines(
    text: str,
    *,
    font_name: str,
    font_size: float,
    width: float,
) -> list[str]:
    words = text.split()
    if not words:
        return []

    lines: list[str] = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if stringWidth(candidate, font_name, font_size) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)

    for line in lines:
        measured = stringWidth(line, font_name, font_size)
        if measured > width:
            raise JournalRenderError(
                "wrapped PDF line exceeds the print-safe width"
            )

    return lines


def render_journal_pdf(
    assembly: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    """Render a deterministic, minimal A4 journal PDF."""

    validate_assembly(assembly)
    _register_embedded_fonts()

    policy = assembly["rendering_policy"]
    if (
        policy.get("tamil_rendering") is not False
        or policy.get("thirukkural_algorithm_usage") != "TITLE_ONLY"
    ):
        raise JournalRenderError("unsupported journal rendering policy")

    output = output_path.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    width, height = A4
    left = 58
    right = 76
    top = 58
    bottom = 52

    # Preserve a conservative print-safe boundary. The additional
    # safety allowance protects against viewer/font substitution.
    print_safety = 10
    usable_width = width - left - right - print_safety

    canvas = Canvas(
        str(output),
        pagesize=A4,
        pageCompression=1,
        invariant=1,
    )
    canvas.setTitle(_latin_text(assembly["title"]))
    canvas.setAuthor("LegalKural")
    canvas.setCreator("LegalKural deterministic journal renderer")
    canvas.setSubject("LegalKural weekly journal")

    page_number = 0

    def footer() -> None:
        canvas.setFont(FONT_REGULAR, 8)
        canvas.drawCentredString(
            width / 2,
            24,
            f"LegalKural | Page {page_number}",
        )

    def new_page() -> float:
        nonlocal page_number
        if page_number:
            footer()
            canvas.showPage()
        page_number += 1
        return height - top

    def ensure_space(y: float, needed: float) -> float:
        if y - needed < bottom:
            return new_page()
        return y

    y = new_page()
    canvas.setFont(FONT_BOLD, 25)
    for line in _wrapped_lines(
        _latin_text(assembly["title"]),
        font_name=FONT_BOLD,
        font_size=25,
        width=usable_width,
    ):
        canvas.drawString(left, y, line)
        y -= 31

    y -= 14
    canvas.setFont(FONT_REGULAR, 12)
    canvas.drawString(
        left,
        y,
        f"Edition: {assembly['edition_date']}",
    )
    y -= 24
    canvas.setFont(FONT_ITALIC, 9)
    canvas.drawString(
        left,
        y,
        "Offline pilot edition - final visual design is deferred.",
    )

    for article in assembly["articles"]:
        y = new_page()

        canvas.setFont(FONT_BOLD, 20)
        for line in _wrapped_lines(
            _latin_text(article["title"]),
            font_name=FONT_BOLD,
            font_size=20,
            width=usable_width,
        ):
            canvas.drawString(left, y, line)
            y -= 25

        y -= 12

        blocks = extract_english_article_blocks(article["content_html"])
        if not blocks:
            raise JournalRenderError(
                f"no renderable English content for {article['case_id']}"
            )

        for tag, text in blocks:
            if tag in {"h1", "h2"}:
                font_name, font_size, leading = FONT_BOLD, 16, 21
                before, after = 13, 7
            elif tag in {"h3", "h4", "h5", "h6"}:
                font_name, font_size, leading = FONT_BOLD, 12, 17
                before, after = 9, 4
            else:
                font_name, font_size, leading = FONT_REGULAR, 10, 14
                before, after = 3, 5
                if tag == "li":
                    text = f"- {text}"

            lines = _wrapped_lines(
                text,
                font_name=font_name,
                font_size=font_size,
                width=usable_width,
            )

            y = ensure_space(y, before + leading)
            y -= before
            canvas.setFont(font_name, font_size)

            for line in lines:
                y = ensure_space(y, leading)

                # ReportLab resets graphics and font state after showPage().
                # Reassert the embedded font for every rendered line.
                canvas.setFont(font_name, font_size)
                canvas.drawString(left, y, line)
                y -= leading

            y -= after

    footer()
    canvas.save()

    reader = PdfReader(str(output))
    extracted = "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )

    if not reader.pages:
        raise JournalRenderError("rendered PDF contains no pages")

    if TAMIL_PATTERN.search(extracted):
        raise JournalRenderError("rendered PDF unexpectedly contains Tamil")

    digest = hashlib.sha256(output.read_bytes()).hexdigest()

    return {
        "schema_version": "1.0",
        "journal_id": assembly["journal_id"],
        "assembly_sha256": assembly["assembly_sha256"],
        "output_path": output.as_posix(),
        "renderer_version": RENDERER_VERSION,
        "pdf_sha256": digest,
        "page_count": len(reader.pages),
        "byte_count": output.stat().st_size,
        "language": "en",
        "tamil_rendered": False,
        "rendering_status": "COMPLETE",
    }
