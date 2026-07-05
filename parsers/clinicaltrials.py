"""ClinicalTrials.gov integration — fetch registration data by NCT ID.

Free API, no key needed. Extracts structured study information.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


def extract_nct_id(text: str) -> Optional[str]:
    """Extract NCT ID from user input (URL or ID string)."""
    text = text.strip()
    m = re.search(r'(NCT\d{8})', text, re.IGNORECASE)
    return m.group(1).upper() if m else None


def fetch_registration(nct_id: str) -> dict:
    """Fetch study registration from ClinicalTrials.gov.

    Returns the raw API response dict (with 'protocolSection' key).
    This preserves the full structured data for direct conversion to ScientificContract.
    """
    url = f"{CTGOV_API}/{nct_id}"

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "RegCheck/1.1",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.error(f"ClinicalTrials.gov API error for {nct_id}: {e}")
        raise ValueError(f"Could not fetch registration {nct_id}: {e}")

    proto = data.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    data["title"] = ident.get("officialTitle") or ident.get("briefTitle", "")
    return data


def registration_to_markdown(reg: dict) -> str:
    """Convert fetched registration to markdown for display/extraction.

    Accepts the raw CT.gov API response (with 'protocolSection' key).
    """
    proto = reg.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    nct_id = ident.get("nctId", reg.get("nct_id", ""))
    title = ident.get("officialTitle") or ident.get("briefTitle", reg.get("title", ""))
    description = proto.get("descriptionModule", {})
    status_mod = proto.get("statusModule", {})
    design_mod = proto.get("designModule", {})
    outcomes_mod = proto.get("outcomesModule", {})
    elig_mod = proto.get("eligibilityModule", {})
    arms_mod = proto.get("armsInterventionsModule", {})

    lines = [
        f"# Study Registration: {nct_id}",
        f"\n## Title\n{title}",
    ]

    brief_summary = description.get("briefSummary", "")
    if brief_summary:
        lines.append(f"\n## Brief Summary\n{brief_summary}")

    lines.append(f"\n## Status: {status_mod.get('overallStatus', '')}")
    phases = design_mod.get("phases", [])
    if phases:
        lines.append(f"Phase: {', '.join(phases)}")

    primary_outcomes = outcomes_mod.get("primaryOutcomes", [])
    if primary_outcomes:
        lines.append("\n## Primary Outcomes")
        for i, o in enumerate(primary_outcomes, 1):
            lines.append(f"{i}. {o.get('measure', '')}")

    secondary_outcomes = outcomes_mod.get("secondaryOutcomes", [])
    if secondary_outcomes:
        lines.append("\n## Secondary Outcomes")
        for i, o in enumerate(secondary_outcomes, 1):
            lines.append(f"{i}. {o.get('measure', '')}")

    eligibility_criteria = elig_mod.get("eligibilityCriteria", "")
    if eligibility_criteria:
        lines.append(f"\n## Eligibility Criteria\n{eligibility_criteria}")

    enrollment = design_mod.get("enrollmentInfo", {}).get("count")
    if enrollment:
        lines.append(f"\n## Planned Enrollment: {enrollment}")

    arms = arms_mod.get("armGroups", [])
    if arms:
        lines.append("\n## Study Arms")
        for arm in arms:
            lines.append(f"- **{arm.get('label', '')}** ({arm.get('type', '')}): {arm.get('description', '')}")

    return "\n".join(lines)
