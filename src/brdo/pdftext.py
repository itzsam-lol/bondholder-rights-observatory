"""Page-level text of retrieved documents, and the normalisation used to compare text."""

import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from pypdf import PageObject, PdfReader
from pypdf.generic import ContentStream

TEXT_EXTRACTOR = "pypdf"

OUTLINED_TEXT_CURVES = 500
"""Curve segments on a page above which glyphs are probably drawn as vector outlines.

Ruled tables use straight lines only, and a logo needs far fewer curves, so a
high count means text that a reader can see may be missing from the text layer.
"""
SCANNED_PAGE_CHARS = 40
"""A page with an image and fewer extracted characters than this is probably a scan."""

_PUNCTUATION = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "‚": "'",
        "‛": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
        " ": " ",
        "₹": "rs.",
    }
)
_LIGATURES = str.maketrans({"\u019f": "ti", "\u01a9": "tt", "\u019e": "tf"})
"""Word exports often map Calibri's ligatures to these letters, turning "ratio" into "ra\u019fo"."""
_WHITESPACE = re.compile(r"\s+")


def repair_ligatures(text: str) -> str:
    return unicodedata.normalize("NFKC", text.translate(_LIGATURES))


def normalize(text: str) -> str:
    """Fold the differences that PDF text extraction introduces but readers ignore.

    Unicode compatibility forms, mis-mapped ligatures, typographic quotes and
    dashes, the rupee sign, letter case and runs of whitespace are all normalised.
    """
    folded = repair_ligatures(text).translate(_PUNCTUATION).lower()
    return _WHITESPACE.sub(" ", folded).strip()


def extract_pages(pdf_path: Path) -> list[str]:
    reader = PdfReader(pdf_path)
    return [page.extract_text() or "" for page in reader.pages]


def page_texts(pdf_path: Path, sha256: str, cache_root: Path) -> list[str]:
    """Return the text of each page, memoised by content hash and extractor."""
    cached = cache_root / "text" / f"{sha256}.{TEXT_EXTRACTOR}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))
    pages = extract_pages(pdf_path)
    cached.parent.mkdir(parents=True, exist_ok=True)
    cached.write_text(json.dumps(pages, ensure_ascii=False), encoding="utf-8")
    return pages


@dataclass(frozen=True)
class PageTextLayer:
    page: int
    characters: int
    curve_segments: int
    images: int
    ocr_font: bool = False

    @property
    def problem(self) -> str | None:
        if self.curve_segments >= OUTLINED_TEXT_CURVES:
            return f"{self.curve_segments} curve segments: text is probably drawn as outlines, not stored as text"
        if self.images and self.characters < SCANNED_PAGE_CHARS:
            return f"{self.images} image(s) and {self.characters} characters: probably a scanned page"
        if self.ocr_font:
            return "the text layer comes from OCR and may contain recognition errors"
        return None


def _has_ocr_font(page: PageObject) -> bool:
    fonts = page.get("/Resources", {}).get("/Font", {})
    return any("GlyphLess" in str(font.get_object().get("/BaseFont", "")) for font in fonts.values())


def audit_text_layer(pdf_path: Path) -> list[PageTextLayer]:
    """Measure, per page, whether the text layer can be trusted to hold what a reader sees."""
    reader = PdfReader(pdf_path)
    audit = []
    for number, page in enumerate(reader.pages, start=1):
        contents = page.get_contents()
        operators = [op for _, op in ContentStream(contents, reader).operations] if contents is not None else []
        audit.append(
            PageTextLayer(
                page=number,
                characters=len(page.extract_text() or ""),
                curve_segments=sum(op in (b"c", b"v", b"y") for op in operators),
                images=len(page.images),
                ocr_font=_has_ocr_font(page),
            )
        )
    return audit
