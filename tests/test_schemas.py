"""Tests for Scientific IR Pydantic models (including new multi-axis severity, evidence graph, uncertainty)."""

import pytest
from schemas.ir import (
    AuditLedger,
    BiasRisk,
    ConfidenceLevel,
    Deviation,
    DeviationJudgement,
    DeviationSeverity,
    DomainSpecificParameters,
    EvidenceEdge,
    EvidenceEdgeType,
    EvidenceGraph,
    EvidenceNode,
    EvidenceNodeType,
    EvidenceSpan,
    ExclusionCriterion,
    Hypothesis,
    HypothesisType,
    MRIParameters,
    MultiAxisSeverity,
    Outcome,
    OutcomeType,
    SampleSize,
    ScientificAnalysis as StatisticalAnalysis,
    ScientificClaim,
    ScientificContract,
    UncertaintyFlag,
)


class TestEvidenceSpan:
    def test_creation(self):
        ev = EvidenceSpan(text="We hypothesized that CBT would reduce anxiety", page=3, source_doc="registration")
        assert ev.text.startswith("We hypothesized")
        assert ev.page == 3

    def test_frozen(self):
        ev = EvidenceSpan(text="test", source_doc="registration")
        with pytest.raises(Exception):
            ev.text = "modified"


class TestUncertaintyFlag:
    def test_default_not_uncertain(self):
        u = UncertaintyFlag()
        assert not u.is_uncertain
        assert u.reason is None

    def test_uncertain_with_reason(self):
        u = UncertaintyFlag(
            is_uncertain=True,
            reason="Table S3 not accessible",
            missing_data=["supplementary_table_s3"],
            resolution_suggestion="Request full-text access",
        )
        assert u.is_uncertain
        assert "Table S3" in u.reason
        assert len(u.missing_data) == 1


class TestEvidenceGraph:
    def test_empty_graph(self):
        eg = EvidenceGraph()
        assert len(eg.nodes) == 0
        assert len(eg.edges) == 0

    def test_add_evidence(self):
        eg = EvidenceGraph(
            nodes=[
                EvidenceNode(id="E1", node_type=EvidenceNodeType.PARAGRAPH, label="Methods section", content="We recruited 200 participants", source_doc="publication"),
                EvidenceNode(id="T1", node_type=EvidenceNodeType.TABLE, label="Table 4", content="ANCOVA results F(2,197)=5.4, p=.005", source_doc="publication"),
            ],
            edges=[
                EvidenceEdge(source_id="E1", target_id="C1", edge_type=EvidenceEdgeType.SUPPORTS, confidence=0.9),
                EvidenceEdge(source_id="T1", target_id="C1", edge_type=EvidenceEdgeType.SUPPORTS, confidence=0.95),
            ],
        )
        assert len(eg.nodes) == 2
        assert len(eg.edges) == 2

    def test_get_supporting_evidence(self):
        eg = EvidenceGraph(
            nodes=[
                EvidenceNode(id="E1", node_type=EvidenceNodeType.PARAGRAPH, label="test", content="content", source_doc="pub"),
                EvidenceNode(id="E2", node_type=EvidenceNodeType.TABLE, label="table", content="data", source_doc="pub"),
            ],
            edges=[
                EvidenceEdge(source_id="E1", target_id="C1", edge_type=EvidenceEdgeType.SUPPORTS),
                EvidenceEdge(source_id="E2", target_id="C1", edge_type=EvidenceEdgeType.SUPPORTS),
                EvidenceEdge(source_id="E2", target_id="C2", edge_type=EvidenceEdgeType.CONTRADICTS),
            ],
        )
        supporting = eg.get_supporting_evidence("C1")
        assert len(supporting) == 2
        contradicting = eg.get_contradicting_evidence("C2")
        assert len(contradicting) == 1

    def test_unsupported_claims(self):
        eg = EvidenceGraph(
            nodes=[EvidenceNode(id="E1", node_type=EvidenceNodeType.PARAGRAPH, label="t", content="c", source_doc="p")],
            edges=[EvidenceEdge(source_id="E1", target_id="C1", edge_type=EvidenceEdgeType.SUPPORTS)],
        )
        unsupported = eg.get_unsupported_claims(["C1", "C2", "C3"])
        assert "C2" in unsupported
        assert "C3" in unsupported
        assert "C1" not in unsupported


class TestMultiAxisSeverity:
    def test_creation(self):
        mas = MultiAxisSeverity(
            scientific_severity=DeviationSeverity.S4_INFERENTIAL,
            bias_risk=BiasRisk.HIGH,
            evidence_quality=ConfidenceLevel.LOW,
            overall_confidence=ConfidenceLevel.MEDIUM,
        )
        assert mas.scientific_severity == DeviationSeverity.S4_INFERENTIAL
        assert mas.bias_risk == BiasRisk.HIGH

    def test_worst_axis(self):
        mas = MultiAxisSeverity(
            scientific_severity=DeviationSeverity.S5_BIAS_CRITICAL,
            bias_risk=BiasRisk.LOW,
        )
        assert mas.worst_axis == "scientific"

    def test_summary(self):
        mas = MultiAxisSeverity(
            scientific_severity=DeviationSeverity.S3_METHODOLOGICAL,
            bias_risk=BiasRisk.MODERATE,
        )
        summary = mas.summary()
        assert "S3" in summary
        assert "moderate" in summary

    def test_uncertain_summary(self):
        mas = MultiAxisSeverity(
            scientific_severity=DeviationSeverity.S2_REPORTING_GAP,
            uncertainty=UncertaintyFlag(is_uncertain=True, reason="missing data"),
        )
        assert "UNCERTAIN" in mas.summary()


class TestScientificClaim:
    def test_provenance_chain(self):
        claim = ScientificClaim(
            id="C1",
            text="Treatment improves memory",
            mapped_hypothesis_id="H1",
            mapped_outcome_ids=["O1"],
            mapped_analysis_ids=["SA1"],
            strength="supported",
        )
        chain = claim.provenance_chain()
        assert chain["claim_id"] == "C1"
        assert chain["hypothesis"] == "H1"
        assert "O1" in chain["outcomes"]
        assert chain["strength"] == "supported"
        assert not chain["uncertain"]

    def test_unsupported_claim(self):
        claim = ScientificClaim(id="C2", text="Exploratory finding", strength="uncertain")
        chain = claim.provenance_chain()
        assert chain["hypothesis"] is None
        assert chain["evidence_count"] == 0


class TestScientificContract:
    def test_full_contract(self):
        contract = ScientificContract(
            doc_id="test_reg", doc_type="registration", title="Test Study",
            hypotheses=[Hypothesis(id="H1", description="Primary", hypothesis_type=HypothesisType.PRIMARY)],
            outcomes=[Outcome(id="O1", measure="GAD-7", outcome_type=OutcomeType.PRIMARY)],
            sample_size=SampleSize(planned_n=100),
        )
        assert len(contract.get_primary_hypotheses()) == 1
        stats = contract.summary_stats()
        assert stats["hypotheses"] == 1

    def test_unsupported_claims(self):
        contract = ScientificContract(
            doc_id="test", doc_type="publication",
            hypotheses=[Hypothesis(id="H1", description="test", hypothesis_type=HypothesisType.PRIMARY)],
            claims=[
                ScientificClaim(id="C1", text="Supported", mapped_hypothesis_id="H1"),
                ScientificClaim(id="C2", text="Unsupported"),
            ],
        )
        unsupported = contract.get_unsupported_claims()
        assert len(unsupported) == 1
        assert unsupported[0].id == "C2"

    def test_evidence_graph_in_contract(self):
        contract = ScientificContract(
            doc_id="test", doc_type="publication",
            evidence_graph=EvidenceGraph(
                nodes=[EvidenceNode(id="E1", node_type=EvidenceNodeType.TABLE, label="Table 1", content="data", source_doc="pub")],
            ),
        )
        assert len(contract.evidence_graph.nodes) == 1
        stats = contract.summary_stats()
        assert stats["evidence_nodes"] == 1


class TestDeviation:
    def test_deviation_with_multi_axis(self):
        d = Deviation(
            id="D-001",
            severity=DeviationSeverity.S3_METHODOLOGICAL,
            multi_axis=MultiAxisSeverity(
                scientific_severity=DeviationSeverity.S3_METHODOLOGICAL,
                bias_risk=BiasRisk.MODERATE,
                evidence_quality=ConfidenceLevel.HIGH,
            ),
            category="analysis_change",
            description="Statistical model changed",
            judgement=DeviationJudgement.DEVIATION,
            confidence=0.85,
            source="graph_diff",
        )
        assert d.multi_axis.bias_risk == BiasRisk.MODERATE
        assert d.multi_axis.worst_axis == "scientific"

    def test_uncertain_deviation(self):
        d = Deviation(
            id="D-002",
            severity=DeviationSeverity.S2_REPORTING_GAP,
            multi_axis=MultiAxisSeverity(
                scientific_severity=DeviationSeverity.S2_REPORTING_GAP,
                uncertainty=UncertaintyFlag(is_uncertain=True, reason="missing data"),
            ),
            category="evidence_gap",
            description="No supporting evidence found",
            judgement=DeviationJudgement.UNCERTAIN,
            confidence=0.4,
            source="semantic_diff",
            uncertainty=UncertaintyFlag(is_uncertain=True, reason="missing data"),
        )
        assert d.judgement == DeviationJudgement.UNCERTAIN
        assert d.uncertainty.is_uncertain


class TestAuditLedger:
    def test_severity_counts(self):
        reg = ScientificContract(doc_id="reg", doc_type="registration")
        pub = ScientificContract(doc_id="pub", doc_type="publication")
        deviations = [
            Deviation(
                id="D-1", severity=DeviationSeverity.S5_BIAS_CRITICAL,
                multi_axis=MultiAxisSeverity(scientific_severity=DeviationSeverity.S5_BIAS_CRITICAL),
                category="test", description="test",
                judgement=DeviationJudgement.DEVIATION, confidence=0.9, source="test",
            ),
        ]
        ledger = AuditLedger(registration_contract=reg, publication_contract=pub, deviations=deviations)
        assert ledger.total_deviations == 1
        assert ledger.severity_counts["S5"] == 1

    def test_uncertainty_summary(self):
        reg = ScientificContract(doc_id="reg", doc_type="registration")
        pub = ScientificContract(doc_id="pub", doc_type="publication")
        deviations = [
            Deviation(
                id="D-1", severity=DeviationSeverity.S2_REPORTING_GAP,
                multi_axis=MultiAxisSeverity(
                    scientific_severity=DeviationSeverity.S2_REPORTING_GAP,
                    uncertainty=UncertaintyFlag(is_uncertain=True, reason="test"),
                ),
                category="test", description="test",
                judgement=DeviationJudgement.UNCERTAIN, confidence=0.4, source="test",
                uncertainty=UncertaintyFlag(is_uncertain=True, reason="test"),
            ),
        ]
        ledger = AuditLedger(registration_contract=reg, publication_contract=pub, deviations=deviations)
        assert ledger.uncertainty_summary is not None
        assert "1" in ledger.uncertainty_summary
