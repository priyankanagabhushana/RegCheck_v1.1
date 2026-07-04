"""Interactive CLI Dashboard for RegCheck v1.1.

Uses Rich for beautiful terminal output showing:
- Side-by-side contract comparison
- Graph diff visualization
- Severity-flagged deviations with evidence
- Editorial query templates
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from schemas.ir import AuditLedger, DeviationSeverity, ScientificContract


console = Console()


def run_dashboard(ledger: AuditLedger) -> None:
    """Render the full interactive dashboard."""
    console.clear()
    _render_banner()
    _render_severity_summary(ledger)
    _render_contract_comparison(ledger)
    _render_deviations_table(ledger)
    _render_editorial_queries(ledger)
    _render_graph_summary(ledger)


def _render_banner() -> None:
    console.print(Panel(
        "[bold cyan]RegCheck v1.1 — Scientific Integrity Engine[/]\n"
        "[dim]Neuro-Symbolic Protocol Deviation Detection[/]",
        border_style="cyan",
    ))
    console.print()


def _render_severity_summary(ledger: AuditLedger) -> None:
    table = Table(title="Severity Distribution", border_style="blue")
    table.add_column("Level", style="bold")
    table.add_column("Classification")
    table.add_column("Count", justify="right")
    table.add_column("Visual")

    severity_info = [
        ("S0", "Trivial", "white"),
        ("S1", "Administrative", "green"),
        ("S2", "Reporting Gap", "yellow"),
        ("S3", "Methodological", "dark_orange"),
        ("S4", "Inferential", "red"),
        ("S5", "Bias-Critical", "bold red"),
    ]

    for sev, label, color in severity_info:
        count = ledger.severity_counts.get(sev, 0)
        bar = "█" * count + "░" * max(0, 10 - count)
        table.add_row(
            f"[{color}]{sev}[/]",
            label,
            str(count),
            f"[{color}]{bar}[/]",
        )

    console.print(table)
    console.print()


def _render_contract_comparison(ledger: AuditLedger) -> None:
    reg = ledger.registration_contract
    pub = ledger.publication_contract

    table = Table(title="Contract Comparison: Registration vs Publication", border_style="cyan")
    table.add_column("Field", style="bold")
    table.add_column("Registration", max_width=40)
    table.add_column("Publication", max_width=40)

    table.add_row("Title", reg.title or "N/A", pub.title or "N/A")
    table.add_row("Hypotheses", str(len(reg.hypotheses)), str(len(pub.hypotheses)))
    table.add_row("Outcomes", str(len(reg.outcomes)), str(len(pub.outcomes)))
    table.add_row("Analyses", str(len(reg.analyses)), str(len(pub.analyses)))

    reg_n = reg.sample_size.planned_n if reg.sample_size else "N/A"
    pub_n = pub.sample_size.actual_n if pub.sample_size and pub.sample_size.actual_n else (
        pub.sample_size.planned_n if pub.sample_size else "N/A"
    )
    table.add_row("Sample Size", f"N={reg_n}", f"N={pub_n}")

    # Primary outcomes
    reg_outcomes = [o.measure for o in reg.get_primary_outcomes()]
    pub_outcomes = [o.measure for o in pub.get_primary_outcomes()]
    table.add_row(
        "Primary Outcomes",
        ", ".join(reg_outcomes) or "N/A",
        ", ".join(pub_outcomes) or "N/A",
    )

    # Primary hypotheses
    reg_hyps = [h.description[:50] + "..." for h in reg.get_primary_hypotheses()]
    pub_hyps = [h.description[:50] + "..." for h in pub.get_primary_hypotheses()]
    table.add_row(
        "Primary Hypotheses",
        "\n".join(reg_hyps) or "N/A",
        "\n".join(pub_hyps) or "N/A",
    )

    console.print(table)
    console.print()


def _render_deviations_table(ledger: AuditLedger) -> None:
    if not ledger.deviations:
        console.print("[green]No deviations detected.[/]")
        return

    table = Table(title=f"Detected Deviations ({ledger.total_deviations})", border_style="red")
    table.add_column("#", style="dim", width=3)
    table.add_column("Sev", width=4)
    table.add_column("Category", max_width=20)
    table.add_column("Description", max_width=50)
    table.add_column("Source", width=12)
    table.add_column("Conf", width=5)

    severity_styles = {
        "S0": "white", "S1": "green", "S2": "yellow",
        "S3": "dark_orange", "S4": "red", "S5": "bold red",
    }

    for i, dev in enumerate(ledger.deviations, 1):
        style = severity_styles.get(dev.severity.value, "white")
        table.add_row(
            str(i),
            f"[{style}]{dev.severity.value}[/]",
            dev.category,
            dev.description[:80],
            dev.source,
            f"{dev.confidence:.0%}",
        )

    console.print(table)
    console.print()


def _render_editorial_queries(ledger: AuditLedger) -> None:
    queries = [
        d for d in ledger.deviations
        if d.editorial_query and d.severity.value >= "S3"
    ]

    if not queries:
        return

    tree = Tree("[bold]Suggested Editorial Queries[/]", guide_style="cyan")
    for dev in queries:
        branch = tree.add(
            f"[{dev.severity.value}] {dev.category}"
        )
        branch.add(f"[dim]{dev.editorial_query}[/]")

    console.print(tree)
    console.print()


def _render_graph_summary(ledger: AuditLedger) -> None:
    if not ledger.graph_diff_summary:
        return

    console.print(Panel(
        ledger.graph_diff_summary,
        title="Graph Diff Summary",
        border_style="dim",
    ))


def render_contract_json(contract: ScientificContract) -> None:
    """Pretty-print a ScientificContract as JSON."""
    import json
    from rich.syntax import Syntax

    json_str = contract.model_dump_json(indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(syntax)
