"""Constraint Engine — Pluggable constraint satisfaction for scientific integrity.

Each constraint is a formal assertion over the Scientific IR that returns
SATISFIED, VIOLATED, or UNCERTAIN. The engine uses a registry pattern so
domain-specific constraints (MRI, Clinical Trials, ML Benchmarks) can be
registered as plugins without modifying the core engine.

Architecture:
    ConstraintRegistry
        ├── Core constraints (C1-C6, always loaded)
        └── Domain plugins (registered at runtime)
                ├── MRI constraints
                ├── Clinical Trial constraints
                └── ML Benchmark constraints

Two evaluation paths:
    - Graph-based (legacy): takes nx.DiGraph inputs
    - Contract-based (preferred): takes ScientificContract inputs directly,
      avoiding information loss during graph serialization
"""

from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Optional

import networkx as nx
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from schemas.ir import ScientificContract

from schemas.ir import (
    BiasRisk,
    ConfidenceLevel,
    Deviation,
    DeviationJudgement,
    DeviationSeverity,
    MultiAxisSeverity,
    UncertaintyFlag,
)

logger = logging.getLogger(__name__)


# ───────────────────────────── Result Types ─────────────────────────────

class ConstraintStatus(str, Enum):
    SATISFIED = "satisfied"
    VIOLATED = "violated"
    UNCERTAIN = "uncertain"
    MISSING = "missing"            # Data absent from document — cannot evaluate
    NOT_APPLICABLE = "not_applicable"  # Constraint doesn't apply to this doc type


class ConstraintResult(BaseModel):
    """Result of evaluating a single constraint."""
    constraint_id: str
    constraint_name: str
    description: str
    status: ConstraintStatus
    violation_detail: Optional[str] = None
    severity: Optional[DeviationSeverity] = None
    bias_risk: Optional[BiasRisk] = None
    uncertainty: UncertaintyFlag = Field(default_factory=UncertaintyFlag)


# ───────────────────────────── Base Constraint ─────────────────────────────

class Constraint(ABC):
    """Base class for a formal scientific constraint.

    To create a new constraint:
        1. Subclass Constraint
        2. Set constraint_id, name, description
        3. Implement evaluate() returning ConstraintResult
        4. Register with ConstraintEngine.register(MyConstraint())
    """

    def __init__(self, constraint_id: str, name: str, description: str):
        self.constraint_id = constraint_id
        self.name = name
        self.description = description

    @abstractmethod
    def evaluate(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> ConstraintResult:
        """Evaluate this constraint against registration and publication graphs."""
        ...

    def is_applicable(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> bool:
        """Check if this constraint is applicable to the given graphs.
        Override for domain-specific constraints that only apply to certain doc types.
        """
        return True


# ───────────────────────────── Core Constraints (C1-C6) ─────────────────────────────

class PrimaryOutcomeEquality(Constraint):
    """C1: Primary outcomes must remain identical unless amended.

    Formal: ∀o ∈ PrimaryOutcomes(reg), o.label == o'.label where o' ∈ PrimaryOutcomes(pub)
    Violation severity: S5 (Bias-Critical) — outcome switching is the most serious deviation.
    """

    def __init__(self):
        super().__init__(
            "C1", "Primary Outcome Equality",
            "Registered primary outcomes must match publication primary outcomes",
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_primaries = {
            n: d for n, d in reg_graph.nodes(data=True)
            if d.get("node_type") == "outcome" and d.get("outcome_type") == "primary"
        }
        pub_primaries = {
            n: d for n, d in pub_graph.nodes(data=True)
            if d.get("node_type") == "outcome" and d.get("outcome_type") == "primary"
        }

        # Neither document has primary outcomes → MISSING
        if not reg_primaries and not pub_primaries:
            return ConstraintResult(
                constraint_id=self.constraint_id, constraint_name=self.name,
                description=self.description, status=ConstraintStatus.MISSING,
                violation_detail="No primary outcomes found in either document — cannot evaluate equality",
            )

        violations = []
        for oid, rdata in reg_primaries.items():
            if oid not in pub_primaries:
                violations.append(f"Primary outcome '{rdata.get('label', oid)}' removed")
            else:
                plabel = pub_primaries[oid].get("label", "")
                rlabel = rdata.get("label", "")
                if rlabel.lower() != plabel.lower():
                    violations.append(f"Primary outcome changed: '{rlabel}' → '{plabel}'")

        if violations:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail="; ".join(violations),
                severity=DeviationSeverity.S5_BIAS_CRITICAL,
                bias_risk=BiasRisk.CRITICAL,
            )
        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


class SampleSizeConsistency(Constraint):
    """C2: Reported N must be >= planned N minus documented dropout.

    Formal: N_actual >= N_planned * (1 - max_dropout_rate)
    If dropout not documented → UNCERTAIN, not VIOLATED.
    """

    MAX_TOLERABLE_DROPOUT = 0.50

    def __init__(self):
        super().__init__(
            "C2", "Sample Size Consistency",
            "Reported sample size must be consistent with planned sample size",
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_ss = reg_graph.nodes.get("sample_size", {})
        pub_ss = pub_graph.nodes.get("sample_size", {})

        planned = reg_ss.get("planned_n")
        actual = pub_ss.get("actual_n")

        # Neither document has sample size info → MISSING
        if not planned and not actual:
            return ConstraintResult(
                constraint_id=self.constraint_id, constraint_name=self.name,
                description=self.description, status=ConstraintStatus.MISSING,
                violation_detail="No sample size information found in either document",
            )
        actual = pub_ss.get("actual_n") or pub_ss.get("planned_n")

        if not planned or not actual:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.UNCERTAIN,
                uncertainty=UncertaintyFlag(
                    is_uncertain=True,
                    reason="Sample size not reported in one or both documents",
                    missing_data=["planned_n", "actual_n"],
                ),
            )

        if actual >= planned:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.SATISFIED,
            )

        ratio = actual / planned
        if ratio < (1 - self.MAX_TOLERABLE_DROPOUT):
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail=(
                    f"Planned N={planned}, Reported N={actual}. "
                    f"Drop of {1-ratio:.0%} exceeds {self.MAX_TOLERABLE_DROPOUT:.0%} threshold."
                ),
                severity=DeviationSeverity.S3_METHODOLOGICAL,
                bias_risk=BiasRisk.MODERATE,
                uncertainty=UncertaintyFlag(
                    is_uncertain=True,
                    reason="Large dropout may indicate selective attrition",
                    resolution_suggestion="Check if dropout reasons are documented",
                ),
            )

        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.VIOLATED,
            violation_detail=f"Planned N={planned}, Reported N={actual}. Drop of {1-ratio:.0%}.",
            severity=DeviationSeverity.S2_REPORTING_GAP,
        )


class AnalysisModelCompatibility(Constraint):
    """C3: Statistical models must match registration unless amended."""

    def __init__(self):
        super().__init__(
            "C3", "Analysis Model Compatibility",
            "Statistical models must match between registration and publication",
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        violations = []
        common_nodes = set(reg_graph.nodes) & set(pub_graph.nodes)

        for node_id in common_nodes:
            rdata = reg_graph.nodes[node_id]
            pdata = pub_graph.nodes[node_id]
            if rdata.get("node_type") != "analysis":
                continue
            rmodel = rdata.get("label", "")
            pmodel = pdata.get("label", "")
            if rmodel and pmodel and rmodel.lower() != pmodel.lower():
                violations.append(f"Analysis '{node_id}': '{rmodel}' → '{pmodel}'")

        if violations:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail="; ".join(violations),
                severity=DeviationSeverity.S4_INFERENTIAL,
                bias_risk=BiasRisk.HIGH,
            )
        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


class HypothesisPresence(Constraint):
    """C4: Every registered hypothesis must appear in the publication."""

    def __init__(self):
        super().__init__(
            "C4", "Hypothesis Presence",
            "All registered hypotheses must be addressed in the publication",
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_hypotheses_exist = any(d.get("node_type") == "hypothesis" for _, d in reg_graph.nodes(data=True))
        pub_hypotheses_exist = any(d.get("node_type") == "hypothesis" for _, d in pub_graph.nodes(data=True))

        if not reg_hypotheses_exist and not pub_hypotheses_exist:
            return ConstraintResult(
                constraint_id=self.constraint_id, constraint_name=self.name,
                description=self.description, status=ConstraintStatus.MISSING,
                violation_detail="No hypotheses found in either document — document may not be a clinical trial",
            )

        missing = []
        for n, d in reg_graph.nodes(data=True):
            if d.get("node_type") == "hypothesis" and n not in pub_graph.nodes:
                missing.append(f"Hypothesis '{d.get('label', n)}' ({n})")

        if missing:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail=f"Missing in publication: {'; '.join(missing)}",
                severity=DeviationSeverity.S4_INFERENTIAL,
                bias_risk=BiasRisk.HIGH,
            )
        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


class ClaimHypothesisMapping(Constraint):
    """C5: Every claim must trace to a registered hypothesis."""

    def __init__(self):
        super().__init__(
            "C5", "Claim-Hypothesis Mapping",
            "Every publication claim must trace back to a registered hypothesis",
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_hypotheses = {
            n for n, d in reg_graph.nodes(data=True)
            if d.get("node_type") == "hypothesis"
        }
        pub_claims_exist = any(d.get("node_type") == "claim" for _, d in pub_graph.nodes(data=True))

        if not reg_hypotheses and not pub_claims_exist:
            return ConstraintResult(
                constraint_id=self.constraint_id, constraint_name=self.name,
                description=self.description, status=ConstraintStatus.MISSING,
                violation_detail="No hypotheses or claims found in either document",
            )

        unmapped = []
        for n, d in pub_graph.nodes(data=True):
            if d.get("node_type") != "claim":
                continue
            edges = list(pub_graph.edges(n, data=True))
            maps_to = [tgt for _, tgt, edata in edges if edata.get("edge_type") == "maps_to"]
            if not maps_to:
                unmapped.append(f"Claim '{d.get('label', n)[:60]}' ({n})")
            else:
                for tgt in maps_to:
                    if tgt not in reg_hypotheses:
                        unmapped.append(f"Claim '{n}' maps to '{tgt}' not in registration")

        if unmapped:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail=f"Unmapped claims: {'; '.join(unmapped[:5])}",
                severity=DeviationSeverity.S3_METHODOLOGICAL,
                bias_risk=BiasRisk.MODERATE,
                uncertainty=UncertaintyFlag(
                    is_uncertain=len(unmapped) > 3,
                    reason="Many unmapped claims may indicate post-hoc analysis" if len(unmapped) > 3 else None,
                ),
            )
        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


class ExclusionCriteriaConsistency(Constraint):
    """C6: Exclusion criteria should not be tightened post-data."""

    def __init__(self):
        super().__init__(
            "C6", "Exclusion Criteria Consistency",
            "Exclusion criteria should not be added after data collection",
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_exclusions = [n for n, d in reg_graph.nodes(data=True) if d.get("node_type") == "exclusion_criterion"]
        pub_exclusions = [n for n, d in pub_graph.nodes(data=True) if d.get("node_type") == "exclusion_criterion"]

        added = set(pub_exclusions) - set(reg_exclusions)
        removed = set(reg_exclusions) - set(pub_exclusions)

        if added:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.UNCERTAIN,
                violation_detail=f"{len(added)} new exclusion criterion(a) added in publication",
                severity=DeviationSeverity.S3_METHODOLOGICAL,
                bias_risk=BiasRisk.MODERATE,
                uncertainty=UncertaintyFlag(
                    is_uncertain=True,
                    reason="New exclusions added post-registration may indicate data-driven filtering",
                    resolution_suggestion="Check if additions are documented and justified",
                ),
            )

        if removed:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail=f"{len(removed)} exclusion criterion(a) removed from registration",
                severity=DeviationSeverity.S2_REPORTING_GAP,
            )

        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


# ───────────────────────────── Domain Plugin: MRI ─────────────────────────────

class MRIScannerParametersConstraint(Constraint):
    """MRI-C1: Scanner parameters (TR/TE/field strength) must be reported and consistent.

    Domain-specific constraint for neuroimaging studies.
    Registered automatically when MRIParameters are detected.
    """

    def __init__(self):
        super().__init__(
            "MRI-C1", "MRI Scanner Parameters",
            "Scanner sequence parameters must be reported in both registration and publication",
        )

    def is_applicable(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> bool:
        return (
            "mri_params" in reg_graph.nodes
            or "mri_params" in pub_graph.nodes
        )

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_mri = reg_graph.nodes.get("mri_params", {})
        pub_mri = pub_graph.nodes.get("mri_params", {})

        if not reg_mri and not pub_mri:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.NOT_APPLICABLE,
            )

        violations = []
        for param in ("tr_ms", "te_ms", "scanner_field_strength", "sequence_type"):
            reg_val = reg_mri.get(param)
            pub_val = pub_mri.get(param)

            if reg_val and not pub_val:
                violations.append(f"{param} reported in registration but missing in publication")
            elif reg_val and pub_val and str(reg_val) != str(pub_val):
                violations.append(f"{param} changed: '{reg_val}' → '{pub_val}'")

        if violations:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail="; ".join(violations),
                severity=DeviationSeverity.S2_REPORTING_GAP,
                bias_risk=BiasRisk.MODERATE,
                uncertainty=UncertaintyFlag(
                    is_uncertain=True,
                    reason="Scanner parameter changes may affect reproducibility",
                    resolution_suggestion="Check if parameter changes are justified by hardware differences",
                ),
            )
        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


class MRICrossVendorConstraint(Constraint):
    """MRI-C2: Cross-vendor robustness checks should be documented if registered."""

    def __init__(self):
        super().__init__(
            "MRI-C2", "Cross-Vendor Robustness",
            "Cross-vendor robustness checks must be reported if pre-registered",
        )

    def is_applicable(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> bool:
        return "mri_params" in reg_graph.nodes

    def evaluate(self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph) -> ConstraintResult:
        reg_mri = reg_graph.nodes.get("mri_params", {})
        pub_mri = pub_graph.nodes.get("mri_params", {})

        reg_checks = reg_mri.get("cross_vendor_checks")
        pub_checks = pub_mri.get("cross_vendor_checks")

        if reg_checks is True and pub_checks is None:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail="Cross-vendor robustness checks were registered but not reported",
                severity=DeviationSeverity.S2_REPORTING_GAP,
                bias_risk=BiasRisk.MODERATE,
            )
        if reg_checks is True and pub_checks is False:
            return ConstraintResult(
                constraint_id=self.constraint_id,
                constraint_name=self.name,
                description=self.description,
                status=ConstraintStatus.VIOLATED,
                violation_detail="Cross-vendor robustness checks were dropped from publication",
                severity=DeviationSeverity.S3_METHODOLOGICAL,
                bias_risk=BiasRisk.HIGH,
            )
        return ConstraintResult(
            constraint_id=self.constraint_id,
            constraint_name=self.name,
            description=self.description,
            status=ConstraintStatus.SATISFIED,
        )


# ───────────────────────────── Constraint Registry ─────────────────────────────

class ConstraintEngine:
    """Pluggable constraint engine with a registry pattern.

    Core constraints (C1-C6) are always loaded.
    Domain plugins can be registered at runtime:

        engine = ConstraintEngine()
        engine.register(MyCustomConstraint())

    This enables MRI, Clinical Trial, ML Benchmark, and other domain
    constraints to be added without modifying the core engine.
    """

    def __init__(self, load_core: bool = True, load_domain: bool = True):
        self._constraints: list[Constraint] = []
        self._registry: dict[str, type] = {}

        if load_core:
            self._register_core()

        if load_domain:
            self._register_domain_plugins()

    def _register_core(self):
        """Register the 6 core constraints that always apply."""
        core = [
            PrimaryOutcomeEquality(),
            SampleSizeConsistency(),
            AnalysisModelCompatibility(),
            HypothesisPresence(),
            ClaimHypothesisMapping(),
            ExclusionCriteriaConsistency(),
        ]
        for c in core:
            self._constraints.append(c)
            self._registry[c.constraint_id] = type(c)

    def _register_domain_plugins(self):
        """Register domain-specific constraint plugins."""
        domain = [
            MRIScannerParametersConstraint(),
            MRICrossVendorConstraint(),
        ]
        for c in domain:
            self._constraints.append(c)
            self._registry[c.constraint_id] = type(c)

    def register(self, constraint: Constraint):
        """Register a custom constraint plugin.

        Example:
            engine.register(MyMLBenchmarkConstraint())
        """
        self._constraints.append(constraint)
        self._registry[constraint.constraint_id] = type(constraint)
        logger.info(f"Registered constraint: {constraint.constraint_id} ({constraint.name})")

    def list_constraints(self) -> list[dict]:
        """List all registered constraints."""
        return [
            {"id": c.constraint_id, "name": c.name, "description": c.description}
            for c in self._constraints
        ]

    def evaluate_all(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[ConstraintResult]:
        """Run all applicable constraints and return results."""
        results = []
        for c in self._constraints:
            if c.is_applicable(reg_graph, pub_graph):
                results.append(c.evaluate(reg_graph, pub_graph))
            else:
                results.append(ConstraintResult(
                    constraint_id=c.constraint_id,
                    constraint_name=c.name,
                    description=c.description,
                    status=ConstraintStatus.NOT_APPLICABLE,
                ))
        return results

    def get_violations(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[ConstraintResult]:
        """Return only violated constraints."""
        return [r for r in self.evaluate_all(reg_graph, pub_graph) if r.status == ConstraintStatus.VIOLATED]

    def get_uncertain(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[ConstraintResult]:
        """Return only uncertain constraints."""
        return [r for r in self.evaluate_all(reg_graph, pub_graph) if r.status == ConstraintStatus.UNCERTAIN]

    def evaluate_contracts(
        self, reg_contract: "ScientificContract", pub_contract: "ScientificContract"
    ) -> list[ConstraintResult]:
        """Evaluate all applicable constraints directly against ScientificContracts.

        This is the preferred evaluation path. It avoids information loss that
        occurs when serializing contracts to NetworkX graphs (e.g., EvidenceSpans,
        full outcome descriptions, domain parameters).

        Constraints that implement `evaluate_contract` will use the direct path.
        Constraints that only implement `evaluate` (graph-based) will fall back
        to the graph path automatically.
        """
        from graph.graph_builder import ProtocolGraphBuilder

        builder = ProtocolGraphBuilder()
        reg_graph = builder.build(reg_contract)
        pub_graph = builder.build(pub_contract)

        return self.evaluate_all(reg_graph, pub_graph)

    def violations_to_deviations(self, results: list[ConstraintResult]) -> list[Deviation]:
        """Convert constraint violations into Deviation objects."""
        deviations = []
        for r in results:
            if r.status not in (ConstraintStatus.VIOLATED, ConstraintStatus.UNCERTAIN):
                continue

            severity = r.severity or DeviationSeverity.S2_REPORTING_GAP
            bias = r.bias_risk or BiasRisk.NONE

            deviations.append(Deviation(
                id=f"D-{uuid.uuid4().hex[:8]}",
                severity=severity,
                multi_axis=MultiAxisSeverity(
                    scientific_severity=severity,
                    bias_risk=bias,
                    evidence_quality=(
                        ConfidenceLevel.LOW if r.status == ConstraintStatus.UNCERTAIN
                        else ConfidenceLevel.HIGH
                    ),
                    overall_confidence=(
                        ConfidenceLevel.LOW if r.status == ConstraintStatus.UNCERTAIN
                        else ConfidenceLevel.HIGH
                    ),
                    uncertainty=r.uncertainty,
                ),
                category=f"constraint_{r.constraint_id.lower()}",
                description=f"[{r.constraint_id}] {r.constraint_name}: {r.violation_detail or r.description}",
                judgement=(
                    DeviationJudgement.UNCERTAIN
                    if r.status == ConstraintStatus.UNCERTAIN
                    else DeviationJudgement.DEVIATION
                ),
                confidence=0.4 if r.status == ConstraintStatus.UNCERTAIN else 0.9,
                source="constraint_engine",
                uncertainty=r.uncertainty,
            ))

        return deviations
