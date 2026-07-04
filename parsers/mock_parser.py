"""Mock Parser - Fallback parser for development and testing.

Accepts pre-parsed Markdown files so downstream work (IR, Graph, Agents)
is never blocked by parsing environment issues.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .base import DocumentParser, ParsedDocument


class MockParser(DocumentParser):
    """Fallback parser that loads pre-cleaned Markdown.

    Accepts:
    - .md files directly as markdown content
    - .json files with {"markdown": "...", "metadata": {...}, "tables": [...]}

    This ensures the IR compilation, graph building, and agent layers
    can always proceed regardless of Docling installation status.
    """

    def parse(self, source: str | Path) -> ParsedDocument:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        if source.suffix == ".json":
            return self._parse_json(source)
        elif source.suffix == ".md":
            return self._parse_markdown(source)
        else:
            raise ValueError(f"MockParser supports .md and .json files, got: {source.suffix}")

    def _parse_json(self, source: Path) -> ParsedDocument:
        with open(source, "r", encoding="utf-8") as f:
            data = json.load(f)

        return ParsedDocument(
            source_path=str(source),
            markdown=data.get("markdown", ""),
            tables=data.get("tables", []),
            metadata=data.get("metadata", {}),
            parser_name="mock_json",
        )

    def _parse_markdown(self, source: Path) -> ParsedDocument:
        with open(source, "r", encoding="utf-8") as f:
            content = f.read()

        return ParsedDocument(
            source_path=str(source),
            markdown=content,
            tables=[],
            metadata={"title": source.stem},
            parser_name="mock_markdown",
        )

    def supports(self, source: str | Path) -> bool:
        source = Path(source)
        return source.suffix.lower() in (".md", ".json")
