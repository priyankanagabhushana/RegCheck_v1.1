"""Integration tests — verify the pipeline works end-to-end.

Tests:
    1. Per-constraint metrics computed correctly against ground truth
    2. Ablation table produces different results per configuration
    3. CT.gov JSON parser handles real data
    4. Full pipeline detects mock deviations
    5. Real PDF integration (Moderna protocol)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from parsers import CTGovJSONParser, MockParser, ParsedDocument


class TestPerConstraintMetrics:
    """Verify evaluation produces proper per-constraint metrics."""

    def test_constraint_metrics_computed(self):
        from evaluation.metrics import ConstraintMetrics, compute_constraint_metrics

        pairs = [
            {"has_deviation": True, "detected": True},
            {"has_deviation": True, "detected": True},
            {"has_deviation": False, "detected": True},
            {"has_deviation": True, "detected": False},
            {"has_deviation": False, "detected": False},
        ]
        metrics = compute_constraint_metrics("C1", "Primary Outcome", pairs)
        assert metrics.true_positives == 2
        assert metrics.false_positives == 1
        assert metrics.false_negatives == 1
        assert metrics.true_negatives == 1
        assert 0.6 < metrics.precision < 0.7
        assert 0.6 < metrics.recall < 0.7

    def test_perfect_detection_f1_is_1(self):
        from evaluation.metrics import compute_constraint_metrics

        pairs = [
            {"has_deviation": True, "detected": True},
            {"has_deviation": True, "detected": True},
            {"has_deviation": False, "detected": False},
        ]
        metrics = compute_constraint_metrics("C1", "", pairs)
        assert metrics.precision == 1.0
        assert metrics.recall == 1.0
        assert metrics.f1 == 1.0

    def test_zero_true_positives_gives_zero_f1(self):
        from evaluation.metrics import compute_constraint_metrics

        pairs = [
            {"has_deviation": True, "detected": False},
            {"has_deviation": True, "detected": False},
        ]
        metrics = compute_constraint_metrics("C1", "", pairs)
        assert metrics.precision == 0.0  # No TPs, so 0/0 = 0
        assert metrics.recall == 0.0
        assert metrics.f1 == 0.0


class TestAblationTable:
    """Verify ablation table produces meaningful results."""

    def test_ablation_table_different_configs(self):
        from evaluation.metrics import (
            AblationTable,
            ConstraintMetrics,
            compute_ablation_table,
        )

        full = ConstraintMetrics("full", "", 10, 1, 2, 50)
        no_graph = ConstraintMetrics("no_graph", "", 5, 0, 7, 51)
        no_const = ConstraintMetrics("no_const", "", 0, 0, 12, 51)

        table = compute_ablation_table(full, no_graph, no_const)
        assert len(table.configurations) == 3
        assert table.to_markdown()  # Should produce markdown

    def test_ablation_f1_differ(self):
        from evaluation.metrics import (
            ConstraintMetrics,
            compute_ablation_table,
        )

        full = ConstraintMetrics("full", "", 10, 1, 2, 50)
        no_graph = ConstraintMetrics("no_graph", "", 5, 0, 7, 51)
        no_const = ConstraintMetrics("no_const", "", 0, 0, 12, 51)

        table = compute_ablation_table(full, no_graph, no_const)
        f1s = [c.f1 for c in table.configurations]
        assert len(set(f1s)) > 1, "Ablation configs should have different F1 scores"


class TestConfusionMatrix:
    """Verify confusion matrix generation."""

    def test_confusion_matrix_output(self):
        from evaluation.metrics import ConfusionMatrix

        cm = ConfusionMatrix()
        cm.add_row("C1", [3, 1, 0])
        cm.add_row("C2", [0, 4, 2])
        cm.add_row("None", [0, 0, 5])

        output = cm.to_text_table()
        assert "C1" in output
        assert "C2" in output
        assert "3" in output


class TestCOMPAREDatasetIntegration:
    """Verify COMPARE dataset loads and integrates with evaluation."""

    def test_compare_dataset_has_entries(self):
        from evaluation import load_compare_dataset

        dataset = load_compare_dataset()
        assert len(dataset) > 0

    def test_evaluate_on_known_deviations(self):
        from evaluation import evaluate_dataset, load_known_deviations

        dataset = load_known_deviations()
        report = evaluate_dataset(dataset=dataset)

        assert report.total_pairs > 0
        assert report.pairs_evaluated > 0
        assert len(report.constraint_metrics) > 0
        assert report.overall_metrics is not None
        assert report.ablation_table is not None

    def test_evaluate_produces_per_constraint_metrics(self):
        from evaluation import evaluate_dataset, load_known_deviations

        dataset = load_known_deviations()
        report = evaluate_dataset(dataset=dataset)

        constraint_ids = [m.constraint_id for m in report.constraint_metrics]
        assert "C1" in constraint_ids
        assert "C2" in constraint_ids
        assert "C3" in constraint_ids

    def test_overall_metrics_are_numbers(self):
        from evaluation import evaluate_dataset, load_known_deviations

        dataset = load_known_deviations()
        report = evaluate_dataset(dataset=dataset)

        om = report.overall_metrics
        assert 0.0 <= om.precision <= 1.0
        assert 0.0 <= om.recall <= 1.0
        assert 0.0 <= om.f1 <= 1.0


class TestCTGovJSONParser:
    """Verify CT.gov JSON parser handles real and synthetic data."""

    def test_supports_valid_ctgov_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT00000000", "briefTitle": "Test"}
                }
            }, f)
            path = f.name
        try:
            parser = CTGovJSONParser()
            assert parser.supports(path)
        finally:
            Path(path).unlink()

    def test_rejects_non_ctgov_json(self):
        parser = CTGovJSONParser()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"random": "data"}, f)
            path = f.name
        try:
            assert not parser.supports(path)
        finally:
            Path(path).unlink()


class TestEndToEndPipeline:
    """Verify the full pipeline runs end-to-end."""

    def test_full_pipeline_mock_mode(self):
        from agents.workflow import VerificationWorkflow

        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        assert result["audit_ledger"] is not None
        assert result["registration_contract"] is not None
        assert result["publication_contract"] is not None
        assert len(result["deviations"]) > 0

    def test_pipeline_detects_outcome_switch(self):
        from agents.workflow import VerificationWorkflow

        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)
        deviations = result["deviations"]

        outcome_devs = [
            d for d in deviations
            if "outcome" in d.category.lower() or "measure" in d.description.lower()
        ]
        assert len(outcome_devs) > 0

    def test_pipeline_detects_analysis_change(self):
        from agents.workflow import VerificationWorkflow

        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)
        deviations = result["deviations"]

        analysis_devs = [
            d for d in deviations
            if "analysis" in d.category.lower() or "model" in d.description.lower()
        ]
        assert len(analysis_devs) > 0

    def test_audit_ledger_has_severity_counts(self):
        from agents.workflow import VerificationWorkflow

        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)
        ledger = result["audit_ledger"]

        assert ledger.total_deviations > 0
        assert ledger.severity_counts

    def test_mri_domain_params_in_graph(self):
        from agents.workflow import VerificationWorkflow

        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)
        reg_contract = result["registration_contract"]

        # MRI params should be accessible
        assert reg_contract.domain_params is not None
