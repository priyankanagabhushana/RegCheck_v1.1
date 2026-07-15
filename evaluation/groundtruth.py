"""Ground-truth data loaders for evaluation.

Two ground-truth sources:
1. Known-deviation pairs: document pairs where we KNOW exactly what changed
   - FDA MRI guidance 2003→2014: SAR table amended, head threshold 3→3.2,
     head/torso and extremities rows removed
2. COMPARE Trials dataset: 72 human-annotated trial pairs with outcome reporting
   bias assessments

For the FDA pair, the ground truth is explicit — the 2014 document states:
"this document was edited to amend a table on specific absorption rate (SAR)"
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class GroundTruth:
    """A single ground-truth entry for a document pair."""
    pair_id: str
    description: str
    source: str  # "known_deviation", "compare_dataset", "manual"

    # Expected outcomes
    expected_primary_outcome_switch: bool = False
    expected_sample_size_discrepancy: bool = False
    expected_analysis_change: bool = False
    expected_hypothesis_missing: bool = False
    expected_exclusion_change: bool = False
    expected_any_s4_or_above: bool = False

    # Metadata
    nct_id: Optional[str] = None
    doi: Optional[str] = None

    # Free-text notes about expected deviations
    expected_deviations_notes: str = ""

    # Scenario identifier for contract-level synthetic evaluation. Keeping this
    # explicit prevents the evaluator from silently reusing one mock case.
    scenario: str = ""


@dataclass
class GroundTruthDataset:
    """A collection of ground-truth entries for systematic evaluation."""
    entries: list[GroundTruth] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.entries)

    def add(self, entry: GroundTruth) -> None:
        self.entries.append(entry)

    def filter_by_source(self, source: str) -> "GroundTruthDataset":
        return GroundTruthDataset(
            entries=[e for e in self.entries if e.source == source]
        )


def load_known_deviations() -> GroundTruthDataset:
    """Load hard-coded known-deviation pairs.

    These are document pairs where we KNOW exactly what changed because
    either the document itself states it (FDA 2014) or we constructed
    synthetic pairs with controlled deviations (mock case studies).
    """
    dataset = GroundTruthDataset()

    # ── FDA MRI Guidance 2003→2014 ──
    # Source: 2014 document explicitly states "edited to amend a table on
    # specific absorption rate (SAR) and make minor formatting and contact updates"
    dataset.add(GroundTruth(
        pair_id="fda_mri_2003_2014",
        description="FDA MRI guidance: SAR table amended (head 3→3.2, 2 rows removed)",
        source="known_deviation",
        expected_any_s4_or_above=True,
        expected_deviations_notes=(
            "SAR table change: head threshold 3→3.2, head/torso row removed, "
            "extremities row removed. Contact info updated. Static field table unchanged."
        ),
        scenario="fda_mri_guidance",
    ))

    # ── Clinical trial case study: outcome switch ──
    dataset.add(GroundTruth(
        pair_id="mock_outcome_switch",
        description="Synthetic: GAD-7→STAI outcome switch, ANCOVA→t-test, N=200→147",
        source="known_deviation",
        expected_primary_outcome_switch=True,
        expected_sample_size_discrepancy=True,
        expected_analysis_change=True,
        expected_hypothesis_missing=True,
        expected_exclusion_change=True,
        expected_any_s4_or_above=True,
        expected_deviations_notes=(
            "6 deviations injected: outcome switch S5, analysis change S4, "
            "sample size discrepancy S2, hypothesis missing S4, exclusion dropped S2, "
            "post-hoc claim S3"
        ),
        scenario="mock_outcome_switch",
    ))

    # ── MRI case study: TR change, cross-vendor drop ──
    dataset.add(GroundTruth(
        pair_id="mock_mri_parameter_change",
        description="Synthetic: TR 2000→1500ms, cross-vendor checks dropped, UQ downgraded",
        source="known_deviation",
        expected_any_s4_or_above=True,
        expected_deviations_notes=(
            "MRI scanner parameter changes: TR changed, cross-vendor robustness "
            "checks dropped, preprocessing pipeline changed"
        ),
        scenario="mock_mri_parameter_change",
    ))

    return dataset


def load_compare_dataset(csv_path: Optional[str | Path] = None) -> GroundTruthDataset:
    """Load the COMPARE Trials project dataset as ground truth.

    The COMPARE project (Goldacre et al., 2019) assessed 67 trials across
    NEJM, Lancet, JAMA, BMJ, and Annals of Internal Medicine. 58/67 (87%)
    had outcome reporting discrepancies.

    Each row provides:
    - NCT ID (registration identifier)
    - Journal, publication link (DOI)
    - Number of pre-specified primary/secondary outcomes
    - How many were correctly reported
    - How many non-pre-specified outcomes were added
    - Whether a correction letter was required

    We treat "number of pre-specified outcomes != number correctly reported"
    as a ground-truth signal for outcome reporting bias.
    """
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / "data" / "study6_compare_trials_dataset" / "compare_trials_72_assessments.csv"

    csv_path = Path(csv_path)
    if not csv_path.exists():
        return GroundTruthDataset()

    dataset = GroundTruthDataset()

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nct_id = ""
            reg_link = row.get("Link to online reistry entry for trial", "")
            if "NCT" in reg_link:
                nct_id = "NCT" + reg_link.split("NCT")[-1].split("/")[0].split("&")[0].rstrip(".")

            pub_link = row.get("Link to online trial report", "")
            doi = ""
            if "doi" in pub_link.lower():
                doi = pub_link

            try:
                pre_prim = int(row.get("Total number of prespecified primary outcomes", "0") or "0")
                rep_prim = int(row.get("Number of prespecified primary outcomes correctly reported", "0") or "0")
                pre_sec = int(row.get("Total number of prespecified secondary outcomes", "0") or "0")
                rep_sec = int(row.get("Number of prespecified secondary outcomes correctly reported", "0") or "0")
                added = int(row.get("Total number of non-prespecified outcomes reported", "0") or "0")
            except ValueError:
                continue

            has_outcome_discrepancy = (pre_prim > rep_prim) or (pre_sec > rep_sec) or (added > 0)

            entry = GroundTruth(
                pair_id=f"compare_{row.get('Study ID', '?')}",
                description=row.get("Trial Title", "")[:200],
                source="compare_dataset",
                expected_primary_outcome_switch=(pre_prim > rep_prim),
                expected_any_s4_or_above=has_outcome_discrepancy,
                nct_id=nct_id if nct_id else None,
                doi=doi if doi else None,
                expected_deviations_notes=(
                    f"COMPARE assessment: {pre_prim} primary ({rep_prim} reported), "
                    f"{pre_sec} secondary ({rep_sec} reported), {added} added"
                ),
            )
            dataset.add(entry)

    return dataset
