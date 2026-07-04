"""Scientific Intermediate Representation (IR) - Core Pydantic Models.

Three-IR Architecture:
  Protocol IR  — What the study *planned* (from registration)
  Execution IR — What the paper *actually reports* (from publication)
  Evidence IR  — Normalized links to every supporting paragraph, table, figure

Every deviation is a transformation between these IRs.
Every extracted object carries full provenance and explicit uncertainty.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ───────────────────────────── Enums ─────────────────────────────

class HypothesisType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPLORATORY = "exploratory"


class OutcomeType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SAFETY = "safety"
    EXPLORATORY = "exploratory"


class DeviationSeverity(str, Enum):
    S0_TRIVIAL = "S0"
    S1_ADMINISTRATIVE = "S1"
    S2_REPORTING_GAP = "S2"
    S3_METHODOLOGICAL = "S3"
    S4_INFERENTIAL = "S4"
    S5_BIAS_CRITICAL = "S5"


class DeviationJudgement(str, Enum):
    DEVIATION = "deviation"
    NO_DEVIATION = "no_deviation"
    MISSING = "missing"
    AMBIGUOUS = "ambiguous"
    UNCERTAIN = "uncertain"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class BiasRisk(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceNodeType(str, Enum):
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    SUPPLEMENT = "supplement"
    FOOTNOTE = "footnote"
    EQUATION = "equation"
    SECTION = "section"


class EvidenceEdgeType(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    MENTIONS = "mentions"
    DERIVED_FROM = "derived_from"
    QUALIFIES = "qualifies"


class RelationshipType(str, Enum):
    TESTED_BY = "tested_by"
    CONSTRAINED_BY = "constrained_by"
    MEASURED_AT = "measured_at"
    SUPPORTED_BY = "supported_by"
    MAPS_TO = "maps_to"
    DEPENDS_ON = "depends_on"
    AMENDS = "amends"


# ───────────────────────────── Uncertainty ─────────────────────────────

class UncertaintyFlag(BaseModel):
    """Explicit uncertainty — the system says 'I don't know' with reasons."""
    is_uncertain: bool = Field(default=False, description="Whether the system is uncertain")
    reason: Optional[str] = Field(default=None, description="Why uncertainty exists")
    missing_data: list[str] = Field(default_factory=list, description="What data would resolve this")
    resolution_suggestion: Optional[str] = Field(
        default=None,
        description="Suggested action: e.g., 'Check supplementary Table S3', 'Need full-text access'"
    )


# ───────────────────────────── Evidence IR ─────────────────────────────

class EvidenceSpan(BaseModel):
    """A provenance-tracked excerpt from a source document."""
    model_config = {"frozen": True}

    text: str = Field(description="The exact quoted text from the source")
    page: Optional[int] = Field(default=None, description="Page number in source PDF")
    bbox: Optional[list[float]] = Field(default=None, description="Bounding box [x0, y0, x1, y1]")
    source_doc: str = Field(description="'registration' or 'publication'")
    section: Optional[str] = Field(default=None, description="Section name (e.g., 'Methods', 'Table 4')")
    chunk_id: Optional[str] = Field(default=None, description="Chunk identifier for retrieval")
    relevance_score: Optional[float] = Field(default=None, description="Retrieval relevance score")


class EvidenceNode(BaseModel):
    """A node in the Evidence Graph: a discrete piece of evidence."""
    id: str = Field(description="Unique evidence node ID, e.g., E1, T2, F3")
    node_type: EvidenceNodeType
    label: str = Field(description="Short description of the evidence")
    content: str = Field(description="Full text content of this evidence piece")
    page: Optional[int] = None
    source_doc: str = Field(description="'registration' or 'publication'")
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)


class EvidenceEdge(BaseModel):
    """An edge in the Evidence Graph: relationship between evidence and scientific objects."""
    source_id: str = Field(description="Evidence node ID")
    target_id: str = Field(description="Target node ID (hypothesis, outcome, claim, etc.)")
    edge_type: EvidenceEdgeType
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    rationale: Optional[str] = Field(default=None, description="Why this edge exists")


class EvidenceGraph(BaseModel):
    """The Evidence IR — a graph linking evidence pieces to scientific objects.

    Nodes: Paragraph, Table, Figure, Supplement, Footnote, Equation, Section
    Edges: supports, contradicts, mentions, derived_from, qualifies

    This is the third IR (after Protocol IR and Execution IR) that makes
    every claim fully traceable through the reasoning chain.
    """
    nodes: list[EvidenceNode] = Field(default_factory=list)
    edges: list[EvidenceEdge] = Field(default_factory=list)

    def get_supporting_evidence(self, target_id: str) -> list[EvidenceNode]:
        """Get all evidence nodes that support a given target."""
        supporting_ids = {
            e.source_id for e in self.edges
            if e.target_id == target_id and e.edge_type == EvidenceEdgeType.SUPPORTS
        }
        return [n for n in self.nodes if n.id in supporting_ids]

    def get_contradicting_evidence(self, target_id: str) -> list[EvidenceNode]:
        """Get all evidence nodes that contradict a given target."""
        contradicting_ids = {
            e.source_id for e in self.edges
            if e.target_id == target_id and e.edge_type == EvidenceEdgeType.CONTRADICTS
        }
        return [n for n in self.nodes if n.id in contradicting_ids]

    def get_unsupported_claims(self, claim_ids: list[str]) -> list[str]:
        """Find claims with no supporting evidence."""
        supported = {
            e.target_id for e in self.edges
            if e.edge_type == EvidenceEdgeType.SUPPORTS
        }
        return [cid for cid in claim_ids if cid not in supported]


# ───────────────────────────── Core Scientific Objects ─────────────────────────────

class Hypothesis(BaseModel):
    """A registered or reported hypothesis."""
    id: str = Field(description="Unique identifier, e.g., H1, H2")
    description: str = Field(description="Full text of the hypothesis")
    hypothesis_type: HypothesisType = Field(description="Primary, secondary, or exploratory")
    variables: list[str] = Field(default_factory=list, description="Key variables mentioned")
    direction: Optional[str] = Field(default=None, description="Directionality: two-sided, greater, less")
    evidence: list[EvidenceSpan] = Field(default_factory=list, description="Source excerpts")
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)

    @field_validator("variables", mode="before")
    @classmethod
    def normalize_variables(cls, v):
        """Accept both strings and dicts from LLM output."""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(item.get("name", item.get("label", str(item))))
            else:
                result.append(str(item))
        return result


class Outcome(BaseModel):
    """A measured outcome variable."""
    id: str = Field(description="Unique identifier, e.g., O1, O2")
    measure: str = Field(description="The measurement instrument or variable name")
    timepoint: Optional[str] = Field(default=None, description="When measured")
    outcome_type: OutcomeType = Field(description="Primary, secondary, safety, exploratory")
    description: Optional[str] = Field(default=None, description="Additional details")
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)


class ExclusionCriterion(BaseModel):
    """A single exclusion/inclusion criterion."""
    id: str
    description: str
    criterion_type: str = Field(description="'inclusion' or 'exclusion'")
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)


class SampleSize(BaseModel):
    """Sample size specification."""
    planned_n: Optional[int] = Field(default=None, description="Planned sample size")
    actual_n: Optional[int] = Field(default=None, description="Actual reported sample size")
    power_analysis: Optional[str] = Field(default=None, description="Power analysis details")
    dropout_rate: Optional[float] = Field(default=None, description="Expected or actual dropout rate")
    justification: Optional[str] = Field(default=None, description="Sample size justification")
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)


class StatisticalAnalysis(BaseModel):
    """A planned or reported statistical analysis."""
    id: str = Field(description="Unique identifier, e.g., SA1")
    model: str = Field(description="Statistical model (e.g., 'ANOVA', 'linear regression', 't-test')")
    dependent_variable: Optional[str] = None
    independent_variables: list[str] = Field(default_factory=list)
    covariates: list[str] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list, description="Multiple comparison corrections")
    software: Optional[str] = None
    evidence: list[EvidenceSpan] = Field(default_factory=list)
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)


class ScientificClaim(BaseModel):
    """A scientific claim made in the publication.

    Full provenance chain: Claim → Hypothesis → Outcome → Statistic → Evidence
    """
    id: str = Field(description="Unique identifier, e.g., C1")
    text: str = Field(description="The claim text")
    mapped_hypothesis_id: Optional[str] = Field(default=None, description="Which hypothesis this tests")
    mapped_outcome_ids: list[str] = Field(default_factory=list, description="Which outcomes support this")
    mapped_analysis_ids: list[str] = Field(default_factory=list, description="Which analyses support this")
    supporting_evidence: list[EvidenceSpan] = Field(default_factory=list)
    strength: Optional[str] = Field(default=None, description="Supported, partially supported, unsupported, uncertain")
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)

    def provenance_chain(self) -> dict:
        """Return the full provenance chain for this claim."""
        return {
            "claim_id": self.id,
            "hypothesis": self.mapped_hypothesis_id,
            "outcomes": self.mapped_outcome_ids,
            "analyses": self.mapped_analysis_ids,
            "evidence_count": len(self.supporting_evidence),
            "strength": self.strength,
            "uncertain": self.uncertainty.is_uncertain,
        }


# ───────────────────────────── Domain-Specific Extensions ─────────────────────────────

class MRIParameters(BaseModel):
    """MRI/Computational imaging specific parameters."""
    model_config = {"frozen": False}

    scanner_field_strength: Optional[float] = Field(default=None, description="Tesla (e.g., 3.0)")
    tr_ms: Optional[float] = Field(default=None, description="Repetition time in ms")
    te_ms: Optional[float] = Field(default=None, description="Echo time in ms")
    voxel_size_mm: Optional[list[float]] = Field(default=None, description="Voxel dimensions [x, y, z]")
    sequence_type: Optional[str] = Field(default=None, description="e.g., T1-weighted, fMRI BOLD")
    region_of_interest: Optional[str] = None
    preprocessing_pipeline: Optional[str] = None
    cross_vendor_checks: Optional[bool] = Field(default=None, description="Cross-vendor robustness verified")
    uncertainty_quantification: Optional[str] = Field(default=None, description="Physics-informed UQ method")


class DomainSpecificParameters(BaseModel):
    """Extensible container for domain-specific parameters."""
    mri: Optional[MRIParameters] = Field(default=None, description="MRI-specific parameters")
    custom: dict[str, Any] = Field(default_factory=dict, description="Arbitrary domain key-value pairs")


# ───────────────────────────── Multi-Axis Severity ─────────────────────────────

class MultiAxisSeverity(BaseModel):
    """Four-axis severity assessment replacing single S0-S5 score.

    Feedback identified that severity should be split into independent axes:
    - scientific_severity: Impact on scientific conclusions (S0-S5)
    - bias_risk: Risk of introducing bias
    - evidence_quality: Quality and completeness of supporting evidence
    - overall_confidence: System's confidence in the deviation detection
    """
    scientific_severity: DeviationSeverity
    bias_risk: BiasRisk = BiasRisk.NONE
    evidence_quality: ConfidenceLevel = ConfidenceLevel.MEDIUM
    overall_confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)

    @property
    def worst_axis(self) -> str:
        """Return the axis with the highest concern."""
        severity_order = {
            DeviationSeverity.S0_TRIVIAL: 0,
            DeviationSeverity.S1_ADMINISTRATIVE: 1,
            DeviationSeverity.S2_REPORTING_GAP: 2,
            DeviationSeverity.S3_METHODOLOGICAL: 3,
            DeviationSeverity.S4_INFERENTIAL: 4,
            DeviationSeverity.S5_BIAS_CRITICAL: 5,
        }
        bias_order = {
            BiasRisk.NONE: 0, BiasRisk.LOW: 1, BiasRisk.MODERATE: 2,
            BiasRisk.HIGH: 3, BiasRisk.CRITICAL: 4,
        }
        scores = {
            "scientific": severity_order.get(self.scientific_severity, 0),
            "bias": bias_order.get(self.bias_risk, 0),
            "evidence": {"high": 3, "medium": 2, "low": 1, "insufficient": 0}.get(
                self.evidence_quality.value, 0
            ),
        }
        return max(scores, key=scores.get)

    def summary(self) -> str:
        parts = [f"Sev={self.scientific_severity.value}"]
        if self.bias_risk != BiasRisk.NONE:
            parts.append(f"Bias={self.bias_risk.value}")
        if self.evidence_quality != ConfidenceLevel.MEDIUM:
            parts.append(f"Evidence={self.evidence_quality.value}")
        if self.uncertainty.is_uncertain:
            parts.append("UNCERTAIN")
        return " | ".join(parts)


# ───────────────────────────── Scientific Contract (Root Model) ─────────────────────────────

class ScientificContract(BaseModel):
    """The root IR representing a compiled scientific document.

    Three-IR Architecture:
    - doc_type='registration' → Protocol IR (what was planned)
    - doc_type='publication' → Execution IR (what was reported)
    - evidence_graph → Evidence IR (normalized links to supporting material)
    """
    doc_id: str = Field(description="Unique identifier for this contract")
    doc_type: str = Field(description="'registration' (Protocol IR) or 'publication' (Execution IR)")
    title: Optional[str] = None
    authors: list[str] = Field(default_factory=list)
    doi: Optional[str] = None
    registration_id: Optional[str] = Field(default=None, description="e.g., ClinicalTrials.gov ID")
    compilation_timestamp: datetime = Field(default_factory=datetime.now)

    hypotheses: list[Hypothesis] = Field(default_factory=list)
    outcomes: list[Outcome] = Field(default_factory=list)
    sample_size: Optional[SampleSize] = None
    exclusion_criteria: list[ExclusionCriterion] = Field(default_factory=list)
    analyses: list[StatisticalAnalysis] = Field(default_factory=list)
    claims: list[ScientificClaim] = Field(default_factory=list)

    domain_params: DomainSpecificParameters = Field(default_factory=DomainSpecificParameters)

    # Evidence IR
    evidence_graph: EvidenceGraph = Field(default_factory=EvidenceGraph)

    raw_markdown: Optional[str] = Field(default=None, description="Original parsed markdown")
    extraction_confidence: Optional[float] = Field(default=None, description="Overall extraction confidence 0-1")
    overall_uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)

    @model_validator(mode="after")
    def validate_hypothesis_references(self) -> "ScientificContract":
        hypothesis_ids = {h.id for h in self.hypotheses}
        for claim in self.claims:
            if claim.mapped_hypothesis_id and claim.mapped_hypothesis_id not in hypothesis_ids:
                pass
        return self

    def get_primary_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.hypothesis_type == HypothesisType.PRIMARY]

    def get_primary_outcomes(self) -> list[Outcome]:
        return [o for o in self.outcomes if o.outcome_type == OutcomeType.PRIMARY]

    def get_unsupported_claims(self) -> list[ScientificClaim]:
        """Find claims that cannot be traced back to any registered hypothesis."""
        hypothesis_ids = {h.id for h in self.hypotheses}
        return [
            c for c in self.claims
            if not c.mapped_hypothesis_id or c.mapped_hypothesis_id not in hypothesis_ids
        ]

    def get_claim_provenance(self) -> list[dict]:
        """Return full provenance chain for every claim."""
        return [c.provenance_chain() for c in self.claims]

    def summary_stats(self) -> dict[str, int]:
        return {
            "hypotheses": len(self.hypotheses),
            "outcomes": len(self.outcomes),
            "exclusion_criteria": len(self.exclusion_criteria),
            "analyses": len(self.analyses),
            "claims": len(self.claims),
            "evidence_nodes": len(self.evidence_graph.nodes),
            "evidence_edges": len(self.evidence_graph.edges),
        }


# ───────────────────────────── Deviation Model ─────────────────────────────

class Deviation(BaseModel):
    """A detected deviation between registration and publication.

    Now includes multi-axis severity, uncertainty, and full provenance.
    """
    id: str = Field(description="Unique deviation identifier")
    severity: DeviationSeverity  # Kept for backward compat
    multi_axis: MultiAxisSeverity = Field(description="Four-axis severity assessment")
    category: str = Field(description="e.g., 'outcome_switch', 'sample_size', 'analysis_change'")
    description: str = Field(description="Human-readable description")
    registration_evidence: list[EvidenceSpan] = Field(default_factory=list)
    publication_evidence: list[EvidenceSpan] = Field(default_factory=list)
    judgement: DeviationJudgement = Field(description="deviation, no_deviation, missing, ambiguous, uncertain")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in this deviation")
    source: str = Field(description="'graph_diff', 'constraint_engine', 'agent', 'semantic_diff', or 'hybrid'")
    editorial_query: Optional[str] = Field(default=None, description="Suggested question for authors (>= S3)")
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)

    # Claim provenance: trace back through the reasoning chain
    linked_hypothesis_id: Optional[str] = None
    linked_outcome_id: Optional[str] = None
    linked_analysis_id: Optional[str] = None


class AuditLedger(BaseModel):
    """The final compiled audit report."""
    registration_contract: ScientificContract
    publication_contract: ScientificContract
    deviations: list[Deviation] = Field(default_factory=list)
    evidence_graph_reg: Optional[EvidenceGraph] = Field(default=None, description="Registration evidence graph")
    evidence_graph_pub: Optional[EvidenceGraph] = Field(default=None, description="Publication evidence graph")
    graph_diff_summary: Optional[str] = None
    constraint_violations: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.now)
    total_deviations: int = 0
    severity_counts: dict[str, int] = Field(default_factory=dict)
    uncertainty_summary: Optional[str] = None

    @model_validator(mode="after")
    def compute_stats(self) -> "AuditLedger":
        self.total_deviations = len(self.deviations)
        counts: dict[str, int] = {}
        for d in self.deviations:
            counts[d.severity.value] = counts.get(d.severity.value, 0) + 1
        self.severity_counts = counts

        uncertain = [d for d in self.deviations if d.uncertainty.is_uncertain]
        if uncertain:
            self.uncertainty_summary = (
                f"{len(uncertain)} deviation(s) flagged as uncertain. "
                "Human review recommended for these items."
            )
        return self


# Alias for backward compatibility
ScientificAnalysis = StatisticalAnalysis
