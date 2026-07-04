"""Docling Parser - Primary PDF parser using IBM's Docling.

Preserves table structures, bounding boxes, and reading order.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .base import DocumentParser, ParsedDocument


class DoclingParser(DocumentParser):
    """Parse PDFs using IBM Docling for layout-aware Markdown extraction.

    Docling preserves:
    - Table structures (as markdown tables)
    - Reading order (column-aware)
    - Section hierarchy (headings)
    - Bounding boxes for provenance tracking
    """

    def __init__(self):
        self._converter = None

    def _get_converter(self):
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter
                self._converter = DocumentConverter()
            except ImportError:
                raise ImportError(
                    "Docling is not installed. Install with: pip install docling\n"
                    "Falling back to MockParser is recommended for development."
                )
        return self._converter

    def parse(self, source: str | Path) -> ParsedDocument:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        converter = self._get_converter()
        result = converter.convert(str(source))

        markdown = result.document.export_to_markdown()

        tables = []
        for table in result.document.tables:
            try:
                table_md = table.export_to_markdown()
                tables.append(table_md)
            except Exception:
                pass

        metadata = {
            "title": getattr(result.document, "title", None),
        }

        return ParsedDocument(
            source_path=str(source),
            markdown=markdown,
            tables=tables,
            metadata=metadata,
            page_count=getattr(result.document, "page_count", None),
            parser_name="docling",
        )

    def supports(self, source: str | Path) -> bool:
        source = Path(source)
        return source.suffix.lower() in (".pdf", ".docx")
