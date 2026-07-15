"""Tests for parsers (MockParser and interface)."""

import json
import pytest
from pathlib import Path

from parsers.mock_parser import MockParser
from parsers.base import ParsedDocument


@pytest.fixture
def sample_md(tmp_path):
    content = """# Study Protocol

## Hypothesis
We hypothesize that cognitive behavioral therapy (CBT) will reduce anxiety scores
by at least 20% compared to waitlist control.

## Methods
### Participants
- Planned N: 200
- Exclusion: Current suicidal ideation

### Outcomes
- Primary: GAD-7 Anxiety Scale (post-intervention)
- Secondary: PHQ-9 Depression Scale (post-intervention)

### Analysis
ANCOVA with baseline GAD-7, age, and gender as covariates.
"""
    path = tmp_path / "test_registration.md"
    path.write_text(content)
    return path


@pytest.fixture
def sample_json(tmp_path):
    data = {
        "markdown": "# Test Document\n\nSample content.",
        "metadata": {"title": "Test", "authors": ["Author A"]},
        "tables": ["| Col1 | Col2 |\n|------|------|\n| A | B |"],
    }
    path = tmp_path / "test.json"
    path.write_text(json.dumps(data))
    return path


class TestMockParser:
    def test_parse_markdown(self, sample_md):
        parser = MockParser()
        doc = parser.parse(sample_md)

        assert isinstance(doc, ParsedDocument)
        assert "Hypothesis" in doc.markdown
        assert doc.parser_name == "mock_markdown"
        assert doc.source_path == str(sample_md)

    def test_parse_json(self, sample_json):
        parser = MockParser()
        doc = parser.parse(sample_json)

        assert isinstance(doc, ParsedDocument)
        assert "Test Document" in doc.markdown
        assert len(doc.tables) == 1
        assert doc.metadata["title"] == "Test"
        assert doc.parser_name == "mock_json"

    def test_supports(self):
        parser = MockParser()
        assert parser.supports(Path("test.md"))
        assert parser.supports(Path("test.json"))
        assert not parser.supports(Path("test.pdf"))

    def test_file_not_found(self):
        parser = MockParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.md"))


class TestParsedDocument:
    def test_model_creation(self):
        doc = ParsedDocument(
            source_path="/test/path.pdf",
            markdown="# Test content",
            parser_name="test",
        )
        assert doc.source_path == "/test/path.pdf"
        assert doc.tables == []
        assert doc.metadata == {}

    def test_with_tables(self):
        doc = ParsedDocument(
            source_path="/test",
            markdown="content",
            tables=["Table 1", "Table 2"],
            parser_name="test",
        )
        assert len(doc.tables) == 2

    def test_pages_default_to_empty(self):
        doc = ParsedDocument(
            source_path="/test",
            markdown="content",
            parser_name="test",
        )
        assert doc.pages == []


class TestPdfParser:
    def test_preserves_all_page_spans(self, tmp_path):
        import fitz

        from parsers.pdf_parser import PyMuPDFParser

        path = tmp_path / "two-pages.pdf"
        pdf = fitz.open()
        pdf.new_page()
        page = pdf.new_page()
        page.insert_text((40, 60), "Second page text")
        pdf.save(path)
        pdf.close()

        parsed = PyMuPDFParser().parse(path)

        assert parsed.page_count == 2
        assert [page.page_number for page in parsed.pages] == [1, 2]
        assert parsed.pages[0].char_end > parsed.pages[0].char_start
        assert "Second page text" in parsed.markdown[parsed.pages[1].char_start:]
