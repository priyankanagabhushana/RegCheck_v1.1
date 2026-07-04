"""Ledger Generator - Compiles graph diffs and agent reasoning into final report.

Produces a structured Markdown audit report with severity flags,
evidence excerpts, and editorial query templates for high-severity deviations.
"""

from __future__ import annotations

from datetime import datetime

from graph.graph_differ import GraphMutation
from schemas.ir import (
    AuditLedger,
    Deviation,
    DeviationSeverity,
    ScientificContract,
)


class LedgerGenerator:
    """Generates the final audit report as an AuditLedger and Markdown."""

    def generate(
        self,
        registration_contract: ScientificContract,
        publication_contract: ScientificContract,
        deviations: list[Deviation],
        constraint_violations: list[str] | None = None,
        graph_mutations: list[GraphMutation] | None = None,
    ) -> AuditLedger:
        """Compile all analysis results into an AuditLedger."""
        graph_summary = None
        if graph_mutations:
            from graph.graph_differ import GraphDiffer
            graph_summary = GraphDiffer.summarize_mutations(graph_mutations)

        ledger = AuditLedger(
            registration_contract=registration_contract,
            publication_contract=publication_contract,
            deviations=sorted(deviations, key=lambda d: self._severity_sort_key(d.severity)),
            graph_diff_summary=graph_summary,
            constraint_violations=constraint_violations or [],
        )

        return ledger

    def render_markdown(self, ledger: AuditLedger) -> str:
        """Render the AuditLedger as a human-readable Markdown report."""
        sections = [
            self._render_header(ledger),
            self._render_summary(ledger),
            self._render_contract_comparison(ledger),
            self._render_deviations(ledger),
            self._render_constraint_violations(ledger),
            self._render_graph_diff(ledger),
            self._render_editorial_queries(ledger),
        ]
        return "\n\n".join(s for s in sections if s)

    def _render_header(self, ledger: AuditLedger) -> str:
        return (
            "# RegCheck v1.1 — Scientific Integrity Audit Report\n\n"
            f"**Generated:** {ledger.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"**Registration:** {ledger.registration_contract.doc_id}\n"
            f"**Publication:** {ledger.publication_contract.doc_id}\n"
            f"**Total Deviations:** {ledger.total_deviations}\n"
        )

    def _render_summary(self, ledger: AuditLedger) -> str:
        severity_emoji = {
            "S0": "⚪", "S1": "🟢", "S2": "🟡", "S3": "🟠", "S4": "🔴", "S5": "🔴"
        }
        lines = ["## Severity Distribution\n"]
        for sev in ["S0", "S1", "S2", "S3", "S4", "S5"]:
            count = ledger.severity_counts.get(sev, 0)
            emoji = severity_emoji.get(sev, "")
            label = DeviationSeverity(sev).name if sev in [s.value for s in DeviationSeverity] else sev
            if count > 0:
                lines.append(f"- {emoji} **{sev}** ({label}): {count}")

        if not ledger.severity_counts:
            lines.append("No deviations detected.")

        return "\n".join(lines)

    def _render_contract_comparison(self, ledger: AuditLedger) -> str:
        reg = ledger.registration_contract
        pub = ledger.publication_contract

        lines = ["## Contract Comparison\n"]
        lines.append("| Field | Registration | Publication |")
        lines.append("|-------|-------------|-------------|")
        lines.append(f"| Title | {reg.title or 'N/A'} | {pub.title or 'N/A'} |")
        lines.append(f"| Hypotheses | {len(reg.hypotheses)} | {len(pub.hypotheses)} |")
        lines.append(f"| Outcomes | {len(reg.outcomes)} | {len(pub.outcomes)} |")
        lines.append(f"| Analyses | {len(reg.analyses)} | {len(pub.analyses)} |")

        reg_n = reg.sample_size.planned_n if reg.sample_size else None
        pub_n = pub.sample_size.actual_n if pub.sample_size and pub.sample_size.actual_n else (
            pub.sample_size.planned_n if pub.sample_size else None
        )
        lines.append(f"| Sample Size | N={reg_n or 'N/A'} | N={pub_n or 'N/A'} |")

        return "\n".join(lines)

    # Clean severity labels
    _SEVERITY_LABELS = {
        "S0": "S0 — Trivial",
        "S1": "S1 — Minor",
        "S2": "S2 — Reporting Gap",
        "S3": "S3 — Methodological",
        "S4": "S4 — Inferential",
        "S5": "S5 — Critical",
    }

    def _render_deviations(self, ledger: AuditLedger) -> str:
        if not ledger.deviations:
            return "## Deviations\n\nNo deviations detected."

        lines = ["## Detected Deviations\n"]

        for i, dev in enumerate(ledger.deviations, 1):
            sev_val = dev.severity.value if hasattr(dev.severity, 'value') else str(dev.severity)
            sev_label = self._SEVERITY_LABELS.get(sev_val, sev_val)
            lines.append(f"### {i}. {sev_label} — {dev.category}")
            lines.append(f"\n{dev.description}\n")
            lines.append(f"- **Source:** {dev.source}")
            lines.append(f"- **Confidence:** {dev.confidence:.0%}")

            if dev.registration_evidence:
                lines.append("- **Registration Evidence:**")
                for ev in dev.registration_evidence:
                    lines.append(f'  > "{ev.text[:200]}..."')

            if dev.publication_evidence:
                lines.append("- **Publication Evidence:**")
                for ev in dev.publication_evidence:
                    lines.append(f'  > "{ev.text[:200]}..."')

            if dev.editorial_query:
                lines.append(f"\n**Suggested Editorial Query:**\n> {dev.editorial_query}")

            lines.append("")

        return "\n".join(lines)

    def _render_constraint_violations(self, ledger: AuditLedger) -> str:
        if not ledger.constraint_violations:
            return ""

        lines = ["## Deterministic Constraint Violations\n"]
        for i, v in enumerate(ledger.constraint_violations, 1):
            lines.append(f"{i}. {v}")

        return "\n".join(lines)

    def _render_graph_diff(self, ledger: AuditLedger) -> str:
        if not ledger.graph_diff_summary:
            return ""

        return f"## Graph Diff Summary\n\n```\n{ledger.graph_diff_summary}\n```"

    def _render_editorial_queries(self, ledger: AuditLedger) -> str:
        queries = [
            d for d in ledger.deviations
            if d.editorial_query and d.severity.value >= "S3"
        ]

        if not queries:
            return ""

        lines = ["## Suggested Editorial Queries\n"]
        lines.append(
            "The following questions are suggested for the authors based on "
            "detected deviations of severity S3 or higher:\n"
        )

        for i, dev in enumerate(queries, 1):
            sev_val = dev.severity.value if hasattr(dev.severity, 'value') else str(dev.severity)
            sev_label = self._SEVERITY_LABELS.get(sev_val, sev_val)
            lines.append(f"**{i}. {sev_label} — {dev.category}:**")
            lines.append(f"> {dev.editorial_query}\n")

        return "\n".join(lines)

    @staticmethod
    def _severity_sort_key(severity: DeviationSeverity) -> int:
        """Sort by severity (highest first)."""
        order = {
            DeviationSeverity.S5_BIAS_CRITICAL: 0,
            DeviationSeverity.S4_INFERENTIAL: 1,
            DeviationSeverity.S3_METHODOLOGICAL: 2,
            DeviationSeverity.S2_REPORTING_GAP: 3,
            DeviationSeverity.S1_ADMINISTRATIVE: 4,
            DeviationSeverity.S0_TRIVIAL: 5,
        }
        return order.get(severity, 99)
