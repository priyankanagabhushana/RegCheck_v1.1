"""Tests for the multi-agent verification workflow (mock mode)."""

import pytest
from agents.workflow import VerificationWorkflow, WorkflowState


class TestVerificationWorkflow:
    def test_mock_workflow_runs(self):
        """Test the full pipeline with mock data."""
        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        assert "audit_ledger" in result
        assert result["audit_ledger"] is not None

    def test_mock_workflow_detects_deviations(self):
        """Mock data should produce deviations."""
        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        ledger = result["audit_ledger"]
        assert ledger.total_deviations > 0

    def test_mock_workflow_has_contracts(self):
        """Both contracts should be populated."""
        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        assert result["registration_contract"] is not None
        assert result["publication_contract"] is not None
        assert result["registration_contract"].doc_type == "registration"
        assert result["publication_contract"].doc_type == "publication"

    def test_mock_workflow_has_graphs(self):
        """Both graphs should be built."""
        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        assert result["registration_graph"] is not None
        assert result["publication_graph"] is not None
        assert result["registration_graph"].number_of_nodes() > 0

    def test_mock_workflow_severity_distribution(self):
        """Mock deviations should have severity scores."""
        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        ledger = result["audit_ledger"]
        assert len(ledger.severity_counts) > 0

    def test_report_generation(self):
        """Markdown report should be generated."""
        from reports.ledger_generator import LedgerGenerator

        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)

        generator = LedgerGenerator()
        md = generator.render_markdown(result["audit_ledger"])

        assert "RegCheck v1.1" in md
        assert "Severity" in md
        assert len(md) > 100
