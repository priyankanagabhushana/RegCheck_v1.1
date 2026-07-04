"""DOI Lookup — fetch paper metadata from CrossRef API.

Free, no API key needed. Returns title, authors, abstract, journal.
"""

from __future__ import annotations

import re
import urllib.request
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

CROSSREF_API = "https://api.crossref.org/works"


def extract_doi(text: str) -> Optional[str]:
    """Extract a DOI from user input (URL, DOI string, or plain text)."""
    text = text.strip()

    # Full URL
    m = re.search(r'doi\.org/(10\.\d{4,}/[^\s]+)', text)
    if m:
        return m.group(1)

    # DOI string
    m = re.search(r'(10\.\d{4,}/[^\s]+)', text)
    if m:
        return m.group(1)

    return None


def fetch_metadata_from_doi(doi: str) -> dict:
    """Fetch paper metadata from CrossRef using a DOI.

    Returns dict with: title, authors, abstract, journal, year, doi, url
    """
    url = f"{CROSSREF_API}/{doi}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RegCheck/1.1 (mailto:regcheck@example.com)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"CrossRef API error for DOI {doi}: {e}")
        raise ValueError(f"Could not fetch metadata for DOI: {doi}")

    msg = data.get("message", {})

    title = msg.get("title", [""])[0] if msg.get("title") else ""
    authors = []
    for a in msg.get("author", []):
        name = f"{a.get('given', '')} {a.get('family', '')}".strip()
        if name:
            authors.append(name)

    abstract = msg.get("abstract", "")
    if abstract:
        # Strip HTML tags
        abstract = re.sub(r'<[^>]+>', '', abstract).strip()

    journal = ""
    if msg.get("container-title"):
        journal = msg["container-title"][0] if msg["container-title"] else ""

    year = None
    if msg.get("published-print"):
        year = msg["published-print"].get("date-parts", [[None]])[0][0]
    elif msg.get("published-online"):
        year = msg["published-online"].get("date-parts", [[None]])[0][0]

    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "journal": journal,
        "year": year,
        "url": f"https://doi.org/{doi}",
    }
