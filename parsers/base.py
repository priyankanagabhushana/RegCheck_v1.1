"""Abstract base for document parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class ParsedDocument(BaseModel):
    """Output of any parser — standardized across all parser implementations."""
    source_path: str = Field(description="Original file path or identifier")
    markdown: str = Field(description="Normalized markdown content")
    tables: list[str] = Field(default_factory=list, description="Extracted table content as markdown")
    metadata: dict = Field(default_factory=dict, description="Document metadata (title, authors, etc.)")
    page_count: Optional[int] = None
    parser_name: str = Field(description="Which parser produced this output")
    raw_text: Optional[str] = Field(default=None, description="Raw text before markdown conversion")


class DocumentParser(ABC):
    """Abstract parser interface.

    All parsers must implement parse() and return a ParsedDocument.
    This ensures downstream components never depend on parser internals.
    """

    @abstractmethod
    def parse(self, source: str | Path) -> ParsedDocument:
        """Parse a document from file path or identifier.

        Args:
            source: File path (PDF/DOCX) or identifier (e.g., ClinicalTrials.gov ID)

        Returns:
            ParsedDocument with normalized markdown and metadata
        """
        ...

    @abstractmethod
    def supports(self, source: str | Path) -> bool:
        """Check if this parser can handle the given source."""
        ...
