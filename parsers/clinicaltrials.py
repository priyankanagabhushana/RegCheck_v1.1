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

    Returns dict with: title, brief_summary, design, outcomes, eligibility, status
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

    # Identification
    ident = proto.get("identificationModule", {})
    title = ident.get("officialTitle") or ident.get("briefTitle", "")
    brief_summary = proto.get("descriptionModule", {}).get("briefSummary", "")

    # Status
    status_mod = proto.get("statusModule", {})
    overall_status = status_mod.get("overallStatus", "")
    start_date = status_mod.get("startDateStruct", {}).get("date", "")
    completion_date = status_mod.get("completionDateStruct", {}).get("date", "")

    # Design
    design_mod = proto.get("designModule", {})
    study_type = design_mod.get("studyType", "")
    phases = design_mod.get("phases", [])
    design_info = design_mod.get("designInfo", {})
    allocation = design_info.get("allocation", "")
    masking = design_info.get("maskingInfo", {}).get("masking", "")
    primary_purpose = design_info.get("primaryPurpose", "")

    # Outcomes
    outcomes_mod = proto.get("outcomesModule", {})
    primary_outcomes = [
        o.get("measure", "") for o in outcomes_mod.get("primaryOutcomes", [])
    ]
    secondary_outcomes = [
        o.get("measure", "") for o in outcomes_mod.get("secondaryOutcomes", [])
    ]

    # Eligibility
    elig_mod = proto.get("eligibilityModule", {})
    eligibility_criteria = elig_mod.get("eligibilityCriteria", "")
    min_age = elig_mod.get("minimumAge", "")
    max_age = elig_mod.get("maximumAge", "")
    sex = elig_mod.get("sex", "")
    healthy_volunteers = elig_mod.get("healthyVolunteers", False)

    # Arms
    arms_mod = proto.get("armsInterventionsModule", {})
    arms = []
    for arm in arms_mod.get("armGroups", []):
        arms.append({
            "label": arm.get("label", ""),
            "type": arm.get("type", ""),
            "description": arm.get("description", ""),
        })

    interventions = []
    for intv in arms_mod.get("interventions", []):
        interventions.append({
            "name": intv.get("name", ""),
            "type": intv.get("type", ""),
            "description": intv.get("description", ""),
        })

    # Sample size
    enroll_info = proto.get("designModule", {}).get("enrollmentInfo", {})
    planned_enrollment = enroll_info.get("count", None)

    # Contacts
    contacts_mod = proto.get("contactsLocationsModule", {})
    central_contacts = []
    for c in contacts_mod.get("centralContacts", []):
        central_contacts.append({
            "name": c.get("name", ""),
            "role": c.get("role", ""),
        })

    return {
        "nct_id": nct_id,
        "title": title,
        "brief_summary": brief_summary,
        "overall_status": overall_status,
        "study_type": study_type,
        "phases": phases,
        "allocation": allocation,
        "masking": masking,
        "primary_purpose": primary_purpose,
        "primary_outcomes": primary_outcomes,
        "secondary_outcomes": secondary_outcomes,
        "eligibility_criteria": eligibility_criteria,
        "min_age": min_age,
        "max_age": max_age,
        "sex": sex,
        "healthy_volunteers": healthy_volunteers,
        "arms": arms,
        "interventions": interventions,
        "planned_enrollment": planned_enrollment,
        "start_date": start_date,
        "completion_date": completion_date,
        "central_contacts": central_contacts,
        "url": f"https://clinicaltrials.gov/study/{nct_id}",
    }


def registration_to_markdown(reg: dict) -> str:
    """Convert fetched registration to markdown for display/extraction."""
    lines = [
        f"# Study Registration: {reg['nct_id']}",
        f"\n## Title\n{reg['title']}",
    ]

    if reg.get("brief_summary"):
        lines.append(f"\n## Brief Summary\n{reg['brief_summary']}")

    lines.append(f"\n## Status: {reg['overall_status']}")
    if reg.get("phases"):
        lines.append(f"Phase: {', '.join(reg['phases'])}")

    if reg.get("primary_outcomes"):
        lines.append("\n## Primary Outcomes")
        for i, o in enumerate(reg["primary_outcomes"], 1):
            lines.append(f"{i}. {o}")

    if reg.get("secondary_outcomes"):
        lines.append("\n## Secondary Outcomes")
        for i, o in enumerate(reg["secondary_outcomes"], 1):
            lines.append(f"{i}. {o}")

    if reg.get("eligibility_criteria"):
        lines.append(f"\n## Eligibility Criteria\n{reg['eligibility_criteria']}")

    if reg.get("planned_enrollment"):
        lines.append(f"\n## Planned Enrollment: {reg['planned_enrollment']}")

    if reg.get("arms"):
        lines.append("\n## Study Arms")
        for arm in reg["arms"]:
            lines.append(f"- **{arm['label']}** ({arm['type']}): {arm['description']}")

    if reg.get("interventions"):
        lines.append("\n## Interventions")
        for intv in reg["interventions"]:
            lines.append(f"- **{intv['name']}** ({intv['type']}): {intv['description']}")

    return "\n".join(lines)
