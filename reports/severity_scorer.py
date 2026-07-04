"""Severity Scorer - Maps mutations and violations to multi-axis severity.

Four axes (from feedback):
1. Scientific Severity (S0-S5) — impact on conclusions
2. Bias Risk — risk of introducing bias
3. Evidence Quality — quality of supporting evidence
4. Confidence — system's confidence in detection

Also handles uncertainty flags and editorial query generation.
"""

from __future__ import annotations

import uuid

from graph.graph_differ import GraphMutation, MutationType, SemanticDriftType
from schemas.ir import (
    BiasRisk,
    ConfidenceLevel,
    Deviation,
    DeviationJudgement,
    DeviationSeverity,
    MultiAxisSeverity,
    UncertaintyFlag,
)


_NODE_TYPE_SEVERITY = {
    "hypothesis": DeviationSeverity.S4_INFERENTIAL,
    "outcome": DeviationSeverity.S5_BIAS_CRITICAL,
    "analysis": DeviationSeverity.S3_METHODOLOGICAL,
    "claim": DeviationSeverity.S3_METHODOLOGICAL,
    "parameter": DeviationSeverity.S2_REPORTING_GAP,
    "exclusion_criterion": DeviationSeverity.S3_METHODOLOGICAL,
}

_ATTRIBUTE_SEVERITY = {
    "label": DeviationSeverity.S2_REPORTING_GAP,
    "model": DeviationSeverity.S4_INFERENTIAL,
    "outcome_type": DeviationSeverity.S5_BIAS_CRITICAL,
    "hypothesis_type": DeviationSeverity.S4_INFERENTIAL,
    "planned_n": DeviationSeverity.S3_METHODOLOGICAL,
    "actual_n": DeviationSeverity.S2_REPORTING_GAP,
    "timepoint": DeviationSeverity.S2_REPORTING_GAP,
    "covariates": DeviationSeverity.S3_METHODOLOGICAL,
    "corrections": DeviationSeverity.S3_METHODOLOGICAL,
    "variables": DeviationSeverity.S2_REPORTING_GAP,
    "direction": DeviationSeverity.S4_INFERENTIAL,
}

_SEMANTIC_DRIFT_SEVERITY = {
    SemanticDriftType.INFERENTIAL_DRIFT: DeviationSeverity.S4_INFERENTIAL,
    SemanticDriftType.OUTCOME_DRIFT: DeviationSeverity.S5_BIAS_CRITICAL,
    SemanticDriftType.HYPOTHESIS_DRIFT: DeviationSeverity.S4_INFERENTIAL,
    SemanticDriftType.EVIDENCE_GAP: DeviationSeverity.S3_METHODOLOGICAL,
    SemanticDriftType.METHODOLOGICAL_DRIFT: DeviationSeverity.S3_METHODOLOGICAL,
}

_SEMANTIC_DRIFT_BIAS = {
    SemanticDriftType.INFERENTIAL_DRIFT: BiasRisk.HIGH,
    SemanticDriftType.OUTCOME_DRIFT: BiasRisk.CRITICAL,
    SemanticDriftType.HYPOTHESIS_DRIFT: BiasRisk.HIGH,
    SemanticDriftType.EVIDENCE_GAP: BiasRisk.MODERATE,
    SemanticDriftType.METHODOLOGICAL_DRIFT: BiasRisk.MODERATE,
}

_EDITORIAL_QUERY_TEMPLATES = {
    "outcome_switch": (
        "The registered primary outcome '{reg}' appears to have been changed to '{pub}' "
        "in the publication. Could you clarify the reason for this change and whether it "
        "was pre-specified in an amendment?"
    ),
    "analysis_change": (
        "The registered statistical analysis ({reg}) was changed to ({pub}) in the "
        "published manuscript. Was this change planned before data analysis? If so, "
        "was it documented in a registration amendment?"
    ),
    "hypothesis_missing": (
        "The registered hypothesis '{reg}' does not appear to be addressed in the "
        "publication. Was this hypothesis dropped? If so, was this decision documented?"
    ),
    "sample_size": (
        "The registered sample size (N={reg}) differs from the reported sample size "
        "(N={pub}). Could you clarify the reason for this discrepancy?"
    ),
    "evidence_gap": (
        "The claim '{claim}' in the publication does not appear to be supported by "
        "a registered hypothesis. Could you clarify the basis for this claim?"
    ),
    "inferential_drift": (
        "The analysis method used to test {outcome} changed from {reg} to {pub} "
        "between registration and publication. Was this change pre-specified?"
    ),
}


class SeverityScorer:
    """Scores mutations and violations into multi-axis Deviation objects."""

    def score_mutation(self, mutation: GraphMutation) -> Deviation | None:
        """Convert a GraphMutation into a severity-scored Deviation."""
        if mutation.is_semantic:
            return self._score_semantic_mutation(mutation)

        severity = self._determine_mutation_severity(mutation)
        if severity is None:
            return None

        category = self._categorize_mutation(mutation)
        editorial_query = self._generate_editorial_query(mutation, category)

        bias_risk = self._determine_bias_risk(severity, category)

        return Deviation(
            id=f"D-{uuid.uuid4().hex[:8]}",
            severity=severity,
            multi_axis=MultiAxisSeverity(
                scientific_severity=severity,
                bias_risk=bias_risk,
                evidence_quality=ConfidenceLevel.MEDIUM,
                overall_confidence=ConfidenceLevel.MEDIUM,
            ),
            category=category,
            description=mutation.description,
            registration_evidence=[],
            publication_evidence=[],
            judgement=DeviationJudgement.DEVIATION,
            confidence=0.8,
            source="graph_diff",
            editorial_query=editorial_query,
        )

    def _score_semantic_mutation(self, mutation: GraphMutation) -> Deviation:
        """Score a semantic drift mutation with appropriate multi-axis severity."""
        drift = mutation.semantic_drift
        severity = _SEMANTIC_DRIFT_SEVERITY.get(
            drift, DeviationSeverity.S3_METHODOLOGICAL
        )
        bias = _SEMANTIC_DRIFT_BIAS.get(drift, BiasRisk.MODERATE)

        category = f"semantic_{drift.value}" if drift else "semantic_drift"
        editorial_query = self._generate_semantic_editorial_query(mutation)

        # Evidence gaps may be uncertain
        uncertainty = UncertaintyFlag()
        if drift == SemanticDriftType.EVIDENCE_GAP:
            uncertainty = UncertaintyFlag(
                is_uncertain=True,
                reason="Claim may be supported by evidence not captured in the graph",
                resolution_suggestion="Check full text and supplementary materials",
            )

        return Deviation(
            id=f"D-{uuid.uuid4().hex[:8]}",
            severity=severity,
            multi_axis=MultiAxisSeverity(
                scientific_severity=severity,
                bias_risk=bias,
                evidence_quality=ConfidenceLevel.LOW if uncertainty.is_uncertain else ConfidenceLevel.MEDIUM,
                overall_confidence=ConfidenceLevel.MEDIUM,
                uncertainty=uncertainty,
            ),
            category=category,
            description=mutation.description,
            registration_evidence=[],
            publication_evidence=[],
            judgement=(
                DeviationJudgement.UNCERTAIN if uncertainty.is_uncertain
                else DeviationJudgement.DEVIATION
            ),
            confidence=0.6 if uncertainty.is_uncertain else 0.75,
            source="semantic_diff",
            editorial_query=editorial_query,
            uncertainty=uncertainty,
        )

    def score_constraint_violation(self, violation: str) -> Deviation:
        """Convert a legacy constraint violation string into a Deviation."""
        severity = DeviationSeverity.S3_METHODOLOGICAL
        category = "constraint_violation"

        keywords = {
            "OUTCOME_SWITCH": (DeviationSeverity.S5_BIAS_CRITICAL, "outcome_switch"),
            "ANALYSIS_CHANGE": (DeviationSeverity.S4_INFERENTIAL, "analysis_change"),
            "HYPOTHESIS_MISSING": (DeviationSeverity.S4_INFERENTIAL, "hypothesis_missing"),
            "SAMPLE_SIZE_VIOLATION": (DeviationSeverity.S3_METHODOLOGICAL, "sample_size"),
        }

        for keyword, (sev, cat) in keywords.items():
            if keyword in violation:
                severity = sev
                category = cat
                break

        return Deviation(
            id=f"D-{uuid.uuid4().hex[:8]}",
            severity=severity,
            multi_axis=MultiAxisSeverity(
                scientific_severity=severity,
                bias_risk=self._determine_bias_risk(severity, category),
                evidence_quality=ConfidenceLevel.HIGH,
                overall_confidence=ConfidenceLevel.HIGH,
            ),
            category=category,
            description=violation,
            judgement=DeviationJudgement.DEVIATION,
            confidence=0.9,
            source="constraint_engine",
            editorial_query=self._generate_constraint_editorial_query(violation),
        )

    def _determine_mutation_severity(self, mutation: GraphMutation) -> DeviationSeverity | None:
        if mutation.mutation_type == MutationType.NODE_REMOVED:
            return _NODE_TYPE_SEVERITY.get(mutation.node_type, DeviationSeverity.S2_REPORTING_GAP)
        if mutation.mutation_type == MutationType.NODE_ADDED:
            return DeviationSeverity.S2_REPORTING_GAP
        if mutation.mutation_type == MutationType.ATTRIBUTE_CHANGED:
            return _ATTRIBUTE_SEVERITY.get(mutation.attribute_name or "", DeviationSeverity.S1_ADMINISTRATIVE)
        if mutation.mutation_type in (MutationType.EDGE_ADDED, MutationType.EDGE_REMOVED):
            return DeviationSeverity.S2_REPORTING_GAP
        return None

    def _determine_bias_risk(self, severity: DeviationSeverity, category: str) -> BiasRisk:
        if severity == DeviationSeverity.S5_BIAS_CRITICAL:
            return BiasRisk.CRITICAL
        if severity == DeviationSeverity.S4_INFERENTIAL:
            return BiasRisk.HIGH
        if severity == DeviationSeverity.S3_METHODOLOGICAL:
            return BiasRisk.MODERATE
        return BiasRisk.LOW

    def _categorize_mutation(self, mutation: GraphMutation) -> str:
        node_type = mutation.node_type or "unknown"
        if mutation.mutation_type == MutationType.ATTRIBUTE_CHANGED:
            attr = mutation.attribute_name or "unknown"
            if attr == "model":
                return "analysis_change"
            if attr in ("outcome_type", "label") and node_type == "outcome":
                return "outcome_switch"
            if attr in ("hypothesis_type", "label") and node_type == "hypothesis":
                return "hypothesis_change"
            if attr in ("planned_n", "actual_n"):
                return "sample_size"
            return f"{node_type}_attribute_change"
        if mutation.mutation_type == MutationType.NODE_REMOVED:
            if node_type == "hypothesis":
                return "hypothesis_missing"
            if node_type == "outcome":
                return "outcome_removed"
            return f"{node_type}_removed"
        if mutation.mutation_type == MutationType.NODE_ADDED:
            return f"{node_type}_added"
        return "structural_change"

    def _generate_editorial_query(self, mutation: GraphMutation, category: str) -> str | None:
        severity = self._determine_mutation_severity(mutation)
        if severity is None or severity.value < "S3":
            return None
        reg_val = str(mutation.registration_value) if mutation.registration_value else "N/A"
        pub_val = str(mutation.publication_value) if mutation.publication_value else "N/A"
        if category == "analysis_change":
            return _EDITORIAL_QUERY_TEMPLATES["analysis_change"].format(reg=reg_val, pub=pub_val)
        if category in ("hypothesis_missing", "hypothesis_change"):
            return _EDITORIAL_QUERY_TEMPLATES["hypothesis_missing"].format(reg=reg_val)
        return None

    def _generate_semantic_editorial_query(self, mutation: GraphMutation) -> str | None:
        drift = mutation.semantic_drift
        if drift == SemanticDriftType.INFERENTIAL_DRIFT:
            reg_val = str(mutation.registration_value) if mutation.registration_value else "N/A"
            pub_val = str(mutation.publication_value) if mutation.publication_value else "N/A"
            return _EDITORIAL_QUERY_TEMPLATES["inferential_drift"].format(
                outcome=mutation.node_id or "the outcome", reg=reg_val, pub=pub_val
            )
        if drift == SemanticDriftType.EVIDENCE_GAP:
            return _EDITORIAL_QUERY_TEMPLATES["evidence_gap"].format(
                claim=mutation.node_id or "this claim"
            )
        return None

    def _generate_constraint_editorial_query(self, violation: str) -> str | None:
        if "OUTCOME_SWITCH" in violation:
            return _EDITORIAL_QUERY_TEMPLATES["outcome_switch"].format(
                reg="registered outcome", pub="different outcome in publication"
            )
        if "SAMPLE_SIZE" in violation:
            return _EDITORIAL_QUERY_TEMPLATES["sample_size"].format(reg="planned", pub="reported")
        return None
