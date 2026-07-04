"""Document Parsers - Ingestion layer for Scientific Integrity Engine.

Provides a pluggable parser interface:
    - DoclingParser: PDF/DOCX via IBM Docling (layout-aware, preserves tables)
    - CTGovJSONParser: ClinicalTrials.gov API v2 JSON → structured markdown
    - MockParser: Markdown/JSON passthrough (development/test fallback)
"""

from .base import DocumentParser, ParsedDocument
from .ctgov_json_parser import CTGovJSONParser
from .docling_parser import DoclingParser
from .mock_parser import MockParser

__all__ = [
    "DocumentParser",
    "ParsedDocument",
    "DoclingParser",
    "CTGovJSONParser",
    "MockParser",
]
