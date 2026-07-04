"""ClinicalTrials.gov JSON Parser — reads CT.gov API v2 JSON into ParsedDocument.

Supports the three-document workflow:
    registration.json → Protocol IR (structured endpoints from CT.gov)
    protocol.pdf     → Protocol IR (detailed SoA/SoE from full protocol)
    publication.pdf  → Execution IR (what was reported)

This parser handles the registration.json file, producing structured markdown
that preserves typed outcomes, eligibility, arms, and enrollment data.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from .base import DocumentParser, ParsedDocument

logger = logging.getLogger(__name__)


class CTGovJSONParser(DocumentParser):
    """Parse ClinicalTrials.gov API v2 JSON into a ParsedDocument.

    Unlike generic PDF parsing, this produces a STRUCTURED markdown where
    outcomes, eligibility criteria, arms, and sample sizes are typed fields
    rather than ambiguous text. This means the ContractExtractor can use
    exact field names rather than relying on LLM guessing.
    """

    def parse(self, source: str | Path) -> ParsedDocument:
        source = Path(source)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        with open(source) as f:
            data = json.load(f)

        proto = data.get("protocolSection", {})
        markdown = self._build_markdown(proto, source)

        tables = self._extract_tables(proto)

        ident = proto.get("identificationModule", {})
        metadata = {
            "nct_id": ident.get("nctId", ""),
            "title": ident.get("briefTitle", ""),
            "official_title": ident.get("officialTitle", ""),
            "source": "clinicaltrials.gov",
            "parser": "ctgov_json",
        }

        return ParsedDocument(
            source_path=str(source),
            markdown=markdown,
            tables=tables,
            metadata=metadata,
            page_count=None,
            parser_name="ctgov_json",
        )

    def supports(self, source: str | Path) -> bool:
        source = Path(source)
        if not source.suffix.lower() == ".json":
            return False
        try:
            with open(source) as f:
                data = json.load(f)
            return "protocolSection" in data or "nct_id" in data
        except (json.JSONDecodeError, KeyError):
            return False

    def _build_markdown(self, proto: dict, source: Path) -> str:
        ident = proto.get("identificationModule", {})
        status = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        outcomes = proto.get("outcomesModule", {})
        eligibility = proto.get("eligibilityModule", {})
        arms = proto.get("armsInterventionsModule", {})

        lines = [
            f"# Study Registration: {ident.get('nctId', source.stem)}",
            "",
            f"## Title",
            ident.get("officialTitle") or ident.get("briefTitle", ""),
            "",
        ]

        brief = proto.get("descriptionModule", {}).get("briefSummary", "")
        if brief:
            lines.extend(["## Brief Summary", brief, ""])

        lines.extend([
            f"## Status: {status.get('overallStatus', 'Unknown')}",
            f"Study Type: {design.get('studyType', 'Unknown')}",
            f"Phase: {', '.join(design.get('phases', ['N/A']))}",
            "",
        ])

        enroll = design.get("enrollmentInfo", {})
        if enroll.get("count"):
            lines.append(f"## Planned Enrollment: {enroll['count']}")

        des_info = design.get("designInfo", {})
        if des_info:
            lines.append(f"Allocation: {des_info.get('allocation', 'N/A')}")
            masking = des_info.get("maskingInfo", {})
            if masking.get("masking"):
                lines.append(f"Masking: {masking['masking']}")
            if des_info.get("primaryPurpose"):
                lines.append(f"Primary Purpose: {des_info['primaryPurpose']}")
        lines.append("")

        primary = outcomes.get("primaryOutcomes", [])
        if primary:
            lines.append("## Primary Outcomes")
            for i, o in enumerate(primary, 1):
                measure = o.get("measure", "?")
                desc = o.get("description", "")
                tf = o.get("timeFrame", "")
                lines.append(f"{i}. **{measure.strip()}**")
                if tf:
                    lines.append(f"   Time Frame: {tf}")
                if desc:
                    lines.append(f"   Description: {desc}")
                lines.append("")

        secondary = outcomes.get("secondaryOutcomes", [])
        if secondary:
            lines.append("## Secondary Outcomes")
            for i, o in enumerate(secondary, 1):
                measure = o.get("measure", "?")
                tf = o.get("timeFrame", "")
                lines.append(f"{i}. **{measure.strip()}**")
                if tf:
                    lines.append(f"   Time Frame: {tf}")
                lines.append("")

        lines.append("## Eligibility Criteria")
        criteria = eligibility.get("eligibilityCriteria", "")
        if criteria:
            lines.append(criteria)
        lines.extend([
            f"Minimum Age: {eligibility.get('minimumAge', 'N/A')}",
            f"Maximum Age: {eligibility.get('maximumAge', 'N/A')}",
            f"Sex: {eligibility.get('sex', 'N/A')}",
            "",
        ])

        arm_groups = arms.get("armGroups", [])
        if arm_groups:
            lines.append("## Study Arms")
            for arm in arm_groups:
                label = arm.get("label", "?")
                atype = arm.get("type", "?")
                desc = arm.get("description", "")
                lines.append(f"- **{label}** ({atype})")
                if desc:
                    lines.append(f"  {desc}")
            lines.append("")

        interventions = arms.get("interventions", [])
        if interventions:
            lines.append("## Interventions")
            for intv in interventions:
                name = intv.get("name", "?")
                itype = intv.get("type", "?")
                lines.append(f"- **{name}** ({itype})")
            lines.append("")

        return "\n".join(lines)

    def _extract_tables(self, proto: dict) -> list[str]:
        tables = []
        outcomes = proto.get("outcomesModule", {})

        primary = outcomes.get("primaryOutcomes", [])
        if primary:
            rows = ["| # | Measure | Time Frame |"]
            rows.append("|---|---------|------------|")
            for i, o in enumerate(primary, 1):
                measure = o.get("measure", "?")[:100]
                tf = o.get("timeFrame", "?")[:60]
                rows.append(f"| P{i} | {measure} | {tf} |")
            tables.append("\n".join(rows))

        secondary = outcomes.get("secondaryOutcomes", [])
        if secondary:
            rows = ["| # | Measure | Time Frame |"]
            rows.append("|---|---------|------------|")
            for i, o in enumerate(secondary, 1):
                measure = o.get("measure", "?")[:100]
                tf = o.get("timeFrame", "?")[:60]
                rows.append(f"| S{i} | {measure} | {tf} |")
            tables.append("\n".join(rows))

        arms = proto.get("armsInterventionsModule", {}).get("armGroups", [])
        if arms:
            rows = ["| Arm | Type | Description |"]
            rows.append("|-----|------|-------------|")
            for arm in arms:
                label = arm.get("label", "?")[:50]
                atype = arm.get("type", "?")[:30]
                desc = (arm.get("description", "") or "")[:100]
                rows.append(f"| {label} | {atype} | {desc} |")
            tables.append("\n".join(rows))

        return tables
