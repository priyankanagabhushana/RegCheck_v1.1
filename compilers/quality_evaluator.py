"""Registration Quality Evaluator — scores how complete/specific a registration is.

Checks for presence and specificity of key elements:
- Hypotheses (are they specific? directional?)
- Outcomes (are measures and timepoints defined?)
- Sample size (is there a power analysis?)
- Analysis plan (are statistical methods specified?)
- Exclusion criteria (are they listed?)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from schemas.ir import ScientificContract


@dataclass
class QualityCriterion:
    name: str
    description: str
    max_score: int
    score: int = 0
    explanation: str = ""


@dataclass
class QualityReport:
    total_score: int = 0
    max_score: int = 0
    percentage: float = 0.0
    grade: str = ""
    criteria: list[QualityCriterion] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


def evaluate_registration_quality(contract: ScientificContract) -> QualityReport:
    """Evaluate how complete and specific a registration is.

    Returns a QualityReport with scores for each criterion and overall grade.
    """
    criteria = []
    recommendations = []

    # 1. Hypotheses
    hyp = _evaluate_hypotheses(contract)
    criteria.append(hyp)
    if hyp.score < hyp.max_score:
        recommendations.append("Specify hypotheses with clear directionality (e.g., 'X will increase Y')")

    # 2. Outcomes
    out = _evaluate_outcomes(contract)
    criteria.append(out)
    if out.score < out.max_score:
        recommendations.append("Define outcome measures with specific instruments and timepoints")

    # 3. Sample size
    ss = _evaluate_sample_size(contract)
    criteria.append(ss)
    if ss.score < ss.max_score:
        recommendations.append("Include a power analysis with effect size justification")

    # 4. Analysis plan
    sa = _evaluate_analysis_plan(contract)
    criteria.append(sa)
    if sa.score < sa.max_score:
        recommendations.append("Specify statistical models, covariates, and correction methods")

    # 5. Exclusion criteria
    ex = _evaluate_exclusion_criteria(contract)
    criteria.append(ex)
    if ex.score < ex.max_score:
        recommendations.append("List all inclusion and exclusion criteria explicitly")

    # 6. Claim-hypothesis mapping
    cl = _evaluate_claims(contract)
    criteria.append(cl)
    if cl.score < cl.max_score:
        recommendations.append("Ensure every planned claim maps to a specific hypothesis")

    total = sum(c.score for c in criteria)
    max_total = sum(c.max_score for c in criteria)
    pct = (total / max_total * 100) if max_total > 0 else 0

    if pct >= 90:
        grade = "A — Excellent"
    elif pct >= 75:
        grade = "B — Good"
    elif pct >= 60:
        grade = "C — Adequate"
    elif pct >= 40:
        grade = "D — Weak"
    else:
        grade = "F — Insufficient"

    return QualityReport(
        total_score=total,
        max_score=max_total,
        percentage=pct,
        grade=grade,
        criteria=criteria,
        recommendations=recommendations,
    )


def _evaluate_hypotheses(contract: ScientificContract) -> QualityCriterion:
    c = QualityCriterion(
        name="Hypotheses",
        description="Are hypotheses specified with clear directionality?",
        max_score=20,
    )
    hyps = contract.hypotheses
    if not hyps:
        c.explanation = "No hypotheses found."
        return c

    c.score += min(10, len(hyps) * 5)  # Up to 10 points for having hypotheses

    # Check for directionality
    directional = [h for h in hyps if h.direction]
    c.score += min(5, len(directional) * 5)

    # Check for primary designation
    primary = [h for h in hyps if h.hypothesis_type.value == "primary"]
    if primary:
        c.score += 5

    c.explanation = f"Found {len(hyps)} hypotheses ({len(primary)} primary, {len(directional)} with direction)."
    return c


def _evaluate_outcomes(contract: ScientificContract) -> QualityCriterion:
    c = QualityCriterion(
        name="Outcomes",
        description="Are outcomes specified with measures and timepoints?",
        max_score=20,
    )
    outs = contract.outcomes
    if not outs:
        c.explanation = "No outcomes found."
        return c

    c.score += min(8, len(outs) * 4)  # Points for having outcomes

    with_measure = [o for o in outs if o.measure]
    c.score += min(4, len(with_measure) * 2)

    with_timepoint = [o for o in outs if o.timepoint]
    c.score += min(4, len(with_timepoint) * 2)

    primary = [o for o in outs if o.outcome_type.value == "primary"]
    if primary:
        c.score += 4

    c.explanation = f"Found {len(outs)} outcomes ({len(primary)} primary). {len(with_timepoint)} have timepoints."
    return c


def _evaluate_sample_size(contract: ScientificContract) -> QualityCriterion:
    c = QualityCriterion(
        name="Sample Size",
        description="Is sample size justified with a power analysis?",
        max_score=15,
    )
    ss = contract.sample_size
    if not ss:
        c.explanation = "No sample size information found."
        return c

    if ss.planned_n:
        c.score += 5
    if ss.power_analysis:
        c.score += 5
    if ss.justification:
        c.score += 3
    if ss.dropout_rate is not None:
        c.score += 2

    c.explanation = f"N={ss.planned_n or '?'}. Power analysis: {'yes' if ss.power_analysis else 'no'}. Dropout: {ss.dropout_rate or 'not specified'}."
    return c


def _evaluate_analysis_plan(contract: ScientificContract) -> QualityCriterion:
    c = QualityCriterion(
        name="Analysis Plan",
        description="Are statistical methods fully specified?",
        max_score=20,
    )
    analyses = contract.analyses
    if not analyses:
        c.explanation = "No analyses found."
        return c

    c.score += min(8, len(analyses) * 4)

    with_model = [a for a in analyses if a.model]
    c.score += min(4, len(with_model) * 2)

    with_covariates = [a for a in analyses if a.covariates]
    c.score += min(4, len(with_covariates) * 2)

    with_corrections = [a for a in analyses if a.corrections]
    c.score += min(4, len(with_corrections) * 2)

    c.explanation = f"Found {len(analyses)} analyses. {len(with_covariates)} specify covariates. {len(with_corrections)} specify corrections."
    return c


def _evaluate_exclusion_criteria(contract: ScientificContract) -> QualityCriterion:
    c = QualityCriterion(
        name="Exclusion Criteria",
        description="Are inclusion/exclusion criteria listed?",
        max_score=15,
    )
    criteria = contract.exclusion_criteria
    if not criteria:
        c.explanation = "No exclusion criteria found."
        return c

    c.score += min(10, len(criteria) * 2)

    inclusion = [e for e in criteria if e.criterion_type == "inclusion"]
    exclusion = [e for e in criteria if e.criterion_type == "exclusion"]
    if inclusion and exclusion:
        c.score += 5

    c.explanation = f"Found {len(criteria)} criteria ({len(inclusion)} inclusion, {len(exclusion)} exclusion)."
    return c


def _evaluate_claims(contract: ScientificContract) -> QualityCriterion:
    c = QualityCriterion(
        name="Claims",
        description="Do claims map to registered hypotheses?",
        max_score=10,
    )
    claims = contract.claims
    if not claims:
        c.explanation = "No claims found (this is fine for a registration)."
        c.score = 10  # Registrations may not have claims
        return c

    mapped = [cl for cl in claims if cl.mapped_hypothesis_id]
    c.score = int(len(mapped) / len(claims) * 10) if claims else 0

    c.explanation = f"Found {len(claims)} claims. {len(mapped)} map to hypotheses."
    return c
