"""PDF Parser with fallback chain: Docling → PyMuPDF.

Handles tables and figures as reliably as possible.
For complex layouts (CONSORT diagrams, multi-column tables),
falls back gracefully and flags uncertainty.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from parsers.base import DocumentParser, PageSpan, ParsedDocument

logger = logging.getLogger(__name__)


class PyMuPDFParser(DocumentParser):
    """PDF parser using PyMuPDF (fitz).

    Strengths: Fast, reliable text extraction, handles most PDFs.
    Weaknesses: Table detection is basic (no column recognition).
    """

    def parse(self, source: str | Path) -> ParsedDocument:
        import fitz  # PyMuPDF

        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        doc = fitz.open(str(source))
        page_blocks: list[str] = []
        page_texts: list[str] = []
        tables = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Extract text with layout preservation
            text = page.get_text("text") or ""
            page_texts.append(text)
            page_blocks.append(f"<!-- Page {page_num + 1} -->\n{text}")

            # Try to extract tables using PyMuPDF's table detection
            try:
                page_tables = page.find_tables()
                for i, table in enumerate(page_tables):
                    md = self._table_to_markdown(table)
                    if md:
                        tables.append(md)
            except Exception:
                pass  # Table detection not available in all PDFs

        metadata = {}
        meta = doc.metadata or {}
        metadata = {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
        }

        page_spans: list[PageSpan] = []
        cursor = 0
        for index, (block, page_text) in enumerate(zip(page_blocks, page_texts), start=1):
            if index > 1:
                cursor += 2  # separator inserted by "\\n\\n".join below
            start = cursor
            cursor += len(block)
            page_spans.append(
                PageSpan(
                    page_number=index,
                    text=page_text,
                    char_start=start,
                    char_end=cursor,
                )
            )

        doc.close()
        markdown = "\n\n".join(page_blocks)

        return ParsedDocument(
            source_path=str(source),
            markdown=markdown,
            tables=tables,
            metadata=metadata,
            page_count=len(page_blocks),
            pages=page_spans,
            parser_name="pymupdf",
            raw_text=markdown,
        )

    def _table_to_markdown(self, table) -> str:
        """Convert a PyMuPDF table to markdown format."""
        try:
            data = table.extract()
            if not data or len(data) < 2:
                return ""

            # Header row
            headers = [str(cell or "").strip() for cell in data[0]]
            md_lines = ["| " + " | ".join(headers) + " |"]
            md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

            # Data rows
            for row in data[1:]:
                cells = [str(cell or "").strip() for cell in row]
                # Pad if needed
                while len(cells) < len(headers):
                    cells.append("")
                md_lines.append("| " + " | ".join(cells[:len(headers)]) + " |")

            return "\n".join(md_lines)
        except Exception:
            return ""

    def supports(self, source: str | Path) -> bool:
        return Path(source).suffix.lower() == ".pdf"


class DoclingParserRobust(DocumentParser):
    """Docling parser with graceful fallback to PyMuPDF.

    Tries Docling first (best table/layout extraction).
    Falls back to PyMuPDF if Docling fails or is not installed.
    """

    def __init__(self):
        self._fallback = PyMuPDFParser()

    def parse(self, source: str | Path) -> ParsedDocument:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        try:
            from docling.document_converter import DocumentConverter
            converter = DocumentConverter()
            result = converter.convert(str(source))

            markdown = result.document.export_to_markdown()
            tables = []
            for table in result.document.tables:
                try:
                    tables.append(table.export_to_markdown())
                except Exception:
                    pass

            return ParsedDocument(
                source_path=str(source),
                markdown=markdown,
                tables=tables,
                metadata={"title": getattr(result.document, "title", None)},
                page_count=getattr(result.document, "page_count", None),
                parser_name="docling",
            )
        except ImportError:
            logger.warning("Docling not installed, falling back to PyMuPDF")
            return self._fallback.parse(source)
        except Exception as e:
            logger.warning(f"Docling failed ({e}), falling back to PyMuPDF")
            return self._fallback.parse(source)

    def supports(self, source: str | Path) -> bool:
        return Path(source).suffix.lower() == ".pdf"


def get_best_parser() -> DocumentParser:
    """Return the best available parser."""
    try:
        parser = DoclingParserRobust()
        return parser
    except Exception:
        return PyMuPDFParser()
