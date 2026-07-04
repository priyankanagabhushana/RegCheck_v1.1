"""COMPARE-based evaluation: tests the comparison pipeline against real-world
deviation patterns from 72 human-annotated clinical trials.

How it works:
    1. For each COMPARE trial, generate a registration contract (what WAS planned)
       and a publication contract (what WAS reported, per COMPARE annotations)
    2. Run constraint engine + graph differ on the pair
    3. Compare detected deviations against COMPARE human annotations

This evaluates the COMPARISON stage (constraint engine + graph differ) against
real-world deviation patterns. The extraction stage (PDF→IR) is a separate
evaluation concern — we provide ground-truth IRs to isolate comparison quality.

Ground truth mapping from COMPARE columns:
    - primary outcomes correctly reported < total prescribed → C1 violation
    - secondary outcomes correctly reported < total prescribed → C4 violation
    - non-prespecified outcomes added > 0 → C5 violation
    - letter required → any S4+ deviation exists
"""

from __future__ import annotations

import csv
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from schemas.ir import (
    DomainSpecificParameters,
    ExclusionCriterion,
    Hypothesis,
    HypothesisType,
    Outcome,
    OutcomeType,
    SampleSize,
    ScientificContract,
    ScientificAnalysis as StatisticalAnalysis,
)


@dataclass
class COMPARETrial:
    """Parsed COMPARE trial entry."""
    study_id: str
    journal: str
    title: str
    nct_id: Optional[str] = None

    # Ground truth from human annotations
    pre_primary: int = 0
    rep_primary: int = 0  # correctly reported
    pre_secondary: int = 0
    rep_secondary: int = 0  # correctly reported
    non_pre_added: int = 0  # novel outcomes added

    letter_required: bool = False
    letter_status: str = ""

    @property
    def c1_violated(self) -> bool:
        """Primary outcome discrepancy."""
        return self.rep_primary < self.pre_primary

    @property
    def c4_violated(self) -> bool:
        """Secondary outcomes incompletely reported."""
        return self.rep_secondary < self.pre_secondary

    @property
    def c5_violated(self) -> bool:
        """Non-prespecified outcomes added."""
        return self.non_pre_added > 0

    @property
    def any_s4_plus(self) -> bool:
        """Any high-severity deviation expected."""
        return self.c1_violated or self.letter_required


def load_compare_trials(csv_path: Optional[Path] = None) -> list[COMPARETrial]:
    """Load COMPARE trials from CSV."""
    if csv_path is None:
        csv_path = Path(__file__).parent.parent / "data" / "study6_compare_trials_dataset" / "compare_trials_72_assessments.csv"

    if not csv_path.exists():
        return []

    trials = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nct = ""
            reg = row.get("Link to online reistry entry for trial", "")
            if "NCT" in reg:
                nct = "NCT" + reg.split("NCT")[-1].split("/")[0].split("&")[0].rstrip(".")

            try:
                pre_prim = int(row.get("Total number of prespecified primary outcomes", "0") or "0")
                rep_prim = int(row.get("Number of prespecified primary outcomes correctly reported", "0") or "0")
                pre_sec = int(row.get("Total number of prespecified secondary outcomes", "0") or "0")
                rep_sec = int(row.get("Number of prespecified secondary outcomes correctly reported", "0") or "0")
                added = int(row.get("Total number of non-prespecified outcomes reported", "0") or "0")
            except ValueError:
                continue

            letter_req = row.get("Final Decision - Letter Required?", "").strip().lower() == "yes"
            letter_status = row.get("Letter Status", "").strip()

            trials.append(COMPARETrial(
                study_id=row.get("Study ID", "?"),
                journal=row.get("Journal Name", "?"),
                title=row.get("Trial Title", "")[:200],
                nct_id=nct if nct else None,
                pre_primary=pre_prim,
                rep_primary=rep_prim,
                pre_secondary=pre_sec,
                rep_secondary=rep_sec,
                non_pre_added=added,
                letter_required=letter_req,
                letter_status=letter_status,
            ))

    return trials


def build_registration_contract(trial: COMPARETrial) -> ScientificContract:
    """Build a realistic registration contract from COMPARE trial data."""
    outcomes = []
    hypotheses = []

    # Primary outcomes (as registered)
    for i in range(trial.pre_primary):
        oid = f"O{i+1}"
        outcomes.append(Outcome(
            id=oid,
            measure=f"Primary Outcome {i+1}",
            timepoint="12 months",
            outcome_type=OutcomeType.PRIMARY,
            description=f"Pre-specified primary outcome {i+1} for {trial.study_id}",
        ))
        if i == 0:
            hypotheses.append(Hypothesis(
                id=f"H{i+1}",
                description=f"Primary hypothesis for {trial.study_id}",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=["outcome", "intervention"],
                direction="two-sided",
            ))

    # Secondary outcomes (as registered)
    for i in range(trial.pre_secondary):
        oid = f"O{trial.pre_primary + i + 1}"
        outcomes.append(Outcome(
            id=oid,
            measure=f"Secondary Outcome {i+1}",
            timepoint="12 months",
            outcome_type=OutcomeType.SECONDARY,
        ))
        if i < 2:
            hypotheses.append(Hypothesis(
                id=f"H{trial.pre_primary + i + 1}",
                description=f"Secondary hypothesis {i+1} for {trial.study_id}",
                hypothesis_type=HypothesisType.SECONDARY,
            ))

    return ScientificContract(
        doc_id=f"reg_{trial.study_id}",
        doc_type="registration",
        title=trial.title,
        registration_id=trial.nct_id,
        hypotheses=hypotheses,
        outcomes=outcomes,
        sample_size=SampleSize(planned_n=500, power_analysis="Power=0.80, alpha=0.05"),
        exclusion_criteria=[
            ExclusionCriterion(id="E1", description="Standard exclusion criteria", criterion_type="exclusion"),
        ],
        analyses=[
            StatisticalAnalysis(id="SA1", model="ANCOVA", dependent_variable="primary outcome",
                              covariates=["baseline"], software="R"),
        ],
        domain_params=DomainSpecificParameters(),
    )


def build_publication_contract(trial: COMPARETrial, reg_contract: ScientificContract) -> ScientificContract:
    """Build a publication contract that reflects COMPARE-annotated deviations.

    Deviations injected based on COMPARE human annotations:
        - If C1 violated: rename some primary outcomes (outcome switch)
        - If C4 violated: remove hypotheses + some secondary outcomes
        - If C5 violated: add novel non-prespecified claims
    """
    pub = reg_contract.model_copy(deep=True)
    pub.doc_id = f"pub_{trial.study_id}"
    pub.doc_type = "publication"

    # C1: primary outcome discrepancy → rename primary outcomes
    if trial.c1_violated:
        for o in pub.outcomes:
            if o.outcome_type == OutcomeType.PRIMARY:
                o.measure = f"Modified Primary {o.id}"
                o.description = f"OUTCOME SWITCHED: changed from registration"

    # C4: secondary outcomes incompletely reported → remove hypotheses + outcomes
    if trial.c4_violated:
        missing_count = trial.pre_secondary - trial.rep_secondary
        secondaries = [o for o in pub.outcomes if o.outcome_type == OutcomeType.SECONDARY]
        to_remove = min(missing_count, len(secondaries))
        for o in secondaries[:to_remove]:
            pub.outcomes.remove(o)
        # Also remove secondary hypotheses
        pub.hypotheses = [h for h in pub.hypotheses if h.hypothesis_type == HypothesisType.PRIMARY]

    # C5: non-prespecified outcomes added → add novel exploratory claims
    if trial.c5_violated:
        import uuid
        for i in range(min(trial.non_pre_added, 3)):
            pub.outcomes.append(Outcome(
                id=f"NEW_O_{i+1}",
                measure=f"Novel Non-Prespecified Outcome {i+1}",
                timepoint="post-hoc",
                outcome_type=OutcomeType.EXPLORATORY,
            ))
        # Add unmapped claims (no hypothesis linkage)
        from schemas.ir import ScientificClaim
        pub.claims.append(ScientificClaim(
            id=f"POSTHOC_C1",
            text=f"Post-hoc finding: novel outcome discovered for {trial.study_id}",
            mapped_hypothesis_id=None,  # Unmapped = post-hoc
            strength="exploratory",
        ))

    # If any discrepancy, also inject sample size marker
    if trial.c1_violated or trial.c4_violated or trial.c5_violated:
        if pub.sample_size:
            pub.sample_size.actual_n = 412

    return pub


def evaluate_compare_pipeline(trials: list[COMPARETrial]) -> dict:
    """Run the comparison pipeline against COMPARE-derived contracts.

    Returns per-constraint metrics: {C1: {tp, fp, fn, precision, recall, f1}, ...}
    """
    from compilers.constraint_engine import ConstraintEngine
    from graph.graph_builder import ProtocolGraphBuilder
    from graph.graph_differ import GraphDiffer
    from reports.severity_scorer import SeverityScorer

    constraints_list = ["C1", "C4", "C5", "OVERALL"]
    results = {c: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for c in constraints_list}

    for trial in trials:
        reg = build_registration_contract(trial)
        pub = build_publication_contract(trial, reg)

        builder = ProtocolGraphBuilder()
        rg = builder.build(reg)
        pg = builder.build(pub)

        differ = GraphDiffer()
        mutations = differ.diff(rg, pg)

        engine = ConstraintEngine(load_core=True, load_domain=True)
        cr = engine.evaluate_all(rg, pg)

        scorer = SeverityScorer()
        devs = engine.violations_to_deviations(cr)
        for m in mutations:
            d = scorer.score_mutation(m)
            if d:
                devs.append(d)

        # Map detections to constraint IDs
        detected = {"C1": False, "C4": False, "C5": False}
        for dev in devs:
            cat = dev.category.lower()
            desc = dev.description.lower()
            src = dev.source
            if "c1" in desc or "primary outcome" in desc or ("outcome" in cat and "primary" in desc):
                detected["C1"] = True
            if "c4" in desc or "hypothesis" in cat or ("hypothesis_missing" in cat):
                detected["C4"] = True
            if "c5" in desc or "claim" in cat or ("unmapped" in desc):
                detected["C5"] = True

        # Ground truth from COMPARE annotations
        gt = {
            "C1": trial.c1_violated,
            "C4": trial.c4_violated,
            "C5": trial.c5_violated,
        }

        # Scoring
        for cid in ["C1", "C4", "C5"]:
            has = gt[cid]
            det = detected[cid]
            if has and det:
                results[cid]["tp"] += 1
            elif not has and det:
                results[cid]["fp"] += 1
            elif has and not det:
                results[cid]["fn"] += 1
            else:
                results[cid]["tn"] += 1

            # Aggregate into OVERALL
            if has and det:
                results["OVERALL"]["tp"] += 1
            elif not has and det:
                results["OVERALL"]["fp"] += 1
            elif has and not det:
                results["OVERALL"]["fn"] += 1
            else:
                results["OVERALL"]["tn"] += 1

    # Compute final metrics
    for cid in constraints_list:
        tp = results[cid]["tp"]
        fp = results[cid]["fp"]
        fn = results[cid]["fn"]
        denom_p = tp + fp
        denom_r = tp + fn
        results[cid]["precision"] = tp / denom_p if denom_p > 0 else 0.0
        results[cid]["recall"] = tp / denom_r if denom_r > 0 else 0.0
        p, r = results[cid]["precision"], results[cid]["recall"]
        results[cid]["f1"] = 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    return results


def format_compare_results(results: dict) -> str:
    """Format COMPARE evaluation results for display."""
    lines = [
        "\n" + "=" * 70,
        "COMPARE DATASET EVALUATION (72 Human-Annotated Clinical Trials)",
        "=" * 70,
        "",
        "Method: Comparison pipeline tested on COMPARE-derived contracts.",
        "Ground truth: Human annotations from Goldacre et al. (2019), Trials, 20(1), 118.",
        "Scope: Evaluates constraint engine + graph differ (extraction quality is separate).",
        "",
        "Per-Constraint Metrics:",
        "| Constraint | Precision | Recall | F1   |  TP |  FP |  FN |",
        "|-----------|-----------|--------|------|-----|-----|-----|",
    ]

    for cid in ["C1", "C4", "C5", "OVERALL"]:
        r = results[cid]
        lines.append(
            f"| {cid:10} | {r['precision']:9.2f} | {r['recall']:6.2f} | {r['f1']:4.2f} | "
            f"{r['tp']:3} | {r['fp']:3} | {r['fn']:3} |"
        )

    lines.extend([
        "",
        "Constraint Descriptions:",
        "  C1: Primary outcome equality (outcome switching detection)",
        "  C4: Hypothesis presence (secondary outcome reporting completeness)",
        "  C5: Claim-hypothesis mapping (novel non-prespecified outcomes)",
        "",
        "Interpretation:",
        "  - C1 recall measures how well we catch primary outcome switches.",
        "  - C4 recall measures how well we flag incompletely reported secondary outcomes.",
        "  - C5 precision measures how well we identify truly novel (non-prespecified) outcomes.",
        "",
        "Limitations:",
        "  - This evaluates the COMPARISON stage, not the full extraction pipeline.",
        "  - Real PDF parsing quality (Docling + LLM extraction) is an additional bottleneck.",
        "  - COMPARE annotations are at the trial level, not individual outcome level.",
    ])

    return "\n".join(lines)
