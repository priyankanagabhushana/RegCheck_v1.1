"""Docling + DeepSeek Vision Parser.

Architecture:
1. Docling extracts structured text + identifies image/chart bounding boxes
2. Images/flowcharts are cropped and sent to DeepSeek V4 Flash Vision API
3. Vision API returns structured description of the visual content
4. Both are merged into a single ParsedDocument

This gives us:
- Excellent text extraction (Docling)
- Excellent table detection (Docling)
- Image/flowchart understanding (DeepSeek Vision)
- Zero GPU cost on our side
"""

from __future__ import annotations

import base64
import io
import logging
import tempfile
from pathlib import Path
from typing import Optional

from parsers.base import DocumentParser, ParsedDocument

logger = logging.getLogger(__name__)


class DoclingVisionParser(DocumentParser):
    """Parse PDFs using Docling for text + DeepSeek Vision for images.

    Step 1: Docling extracts text, tables, and identifies image regions
    Step 2: Image regions are cropped and sent to DeepSeek Vision API
    Step 3: Vision descriptions are merged into the document
    """

    def __init__(self, api_key: str, model: str = "deepseek/deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self._fallback = None

    def parse(self, source: str | Path) -> ParsedDocument:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        # Step 1: Docling extraction
        docling_result = self._extract_with_docling(source)

        # Step 2: Extract images and describe them with Vision API
        image_descriptions = self._describe_images_with_vision(source, docling_result)

        # Step 3: Merge
        markdown = docling_result.markdown
        if image_descriptions:
            markdown += "\n\n---\n\n## Image and Flowchart Descriptions\n\n"
            for desc in image_descriptions:
                markdown += f"\n{desc}\n"

        return ParsedDocument(
            source_path=str(source),
            markdown=markdown,
            tables=docling_result.tables,
            metadata=docling_result.metadata,
            page_count=docling_result.page_count,
            parser_name="docling+deepseek_vision",
            raw_text=docling_result.raw_text,
        )

    def _extract_with_docling(self, source: Path) -> ParsedDocument:
        """Use Docling for text and table extraction."""
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
                raw_text=markdown,
            )
        except ImportError:
            logger.warning("Docling not installed, falling back to PyMuPDF")
            return self._fallback_parse(source)
        except Exception as e:
            logger.warning(f"Docling failed: {e}, falling back to PyMuPDF")
            return self._fallback_parse(source)

    def _fallback_parse(self, source: Path) -> ParsedDocument:
        """Fallback to PyMuPDF if Docling is not available."""
        from parsers.pdf_parser import PyMuPDFParser
        return PyMuPDFParser().parse(source)

    def _describe_images_with_vision(
        self, source: Path, docling_result: ParsedDocument
    ) -> list[str]:
        """Extract images from PDF and describe them using DeepSeek Vision API."""
        descriptions = []

        try:
            images = self._extract_images_from_pdf(source)
            if not images:
                return descriptions

            logger.info(f"Found {len(images)} images/figures in PDF, describing with Vision API...")

            for i, img_data in enumerate(images):
                try:
                    desc = self._describe_single_image(img_data, i + 1)
                    if desc:
                        descriptions.append(f"### Figure {i + 1}\n\n{desc}")
                except Exception as e:
                    logger.warning(f"Failed to describe image {i+1}: {e}")
                    descriptions.append(f"### Figure {i + 1}\n\n[Could not describe: {e}]")

        except Exception as e:
            logger.warning(f"Image extraction failed: {e}")

        return descriptions

    def _extract_images_from_pdf(self, source: Path) -> list[bytes]:
        """Extract images/figures from PDF pages using PyMuPDF.

        Returns list of PNG image bytes for each page that contains figures.
        """
        import fitz

        images = []
        doc = fitz.open(str(source))

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Check if page has images
            image_list = page.get_images(full=True)
            if not image_list:
                continue

            # Check if page has significant visual content (not just embedded tiny icons)
            # Render the page as an image
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for quality
            pix = page.get_pixmap(matrix=mat)

            # Only include if the page has substantial image content
            # (filter out pages that just have small logos/icons)
            if len(image_list) >= 1:
                img_bytes = pix.tobytes("png")
                # Only include if image is reasonably sized (>50KB suggests real content)
                if len(img_bytes) > 50000:
                    images.append(img_bytes)

        doc.close()
        return images

    def _describe_single_image(self, img_bytes: bytes, figure_num: int) -> str:
        """Describe a single image using DeepSeek Vision API via LiteLLM."""
        import litellm

        # Encode image to base64
        b64 = base64.b64encode(img_bytes).decode("utf-8")

        response = litellm.completion(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Describe this figure from a scientific paper in detail. "
                                "If it is a flowchart, describe each step and decision point. "
                                "If it is a table, extract the data. "
                                "If it is a chart/graph, describe the axes, data series, and key findings. "
                                "If it is a CONSORT diagram, describe the flow of participants. "
                                "Be precise and include all numbers, labels, and text you can see."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=1000,
        )

        return response.choices[0].message.content

    def supports(self, source: str | Path) -> bool:
        return Path(source).suffix.lower() == ".pdf"


def get_parser_with_vision(api_key: str, model: str = "deepseek/deepseek-chat") -> DocumentParser:
    """Get the best available parser with DeepSeek Vision support."""
    return DoclingVisionParser(api_key=api_key, model=model)
