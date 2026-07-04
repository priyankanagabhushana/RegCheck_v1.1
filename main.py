"""RegCheck v1.1 — Scientific Integrity Engine CLI.

Usage:
    python main.py demo                                    # Mock demo (no LLM)
    python main.py compare <reg> <pub>                     # Compare two documents
    python main.py eval                                    # Run evaluation suite
    python main.py eval --ablation                         # Ablation study
    python main.py eval --dataset compare                  # COMPARE dataset eval
    python main.py schema                                  # Display IR schema
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="regcheck-v11",
    help="Scientific Integrity Engine — Neuro-symbolic protocol deviation detection",
)
console = Console()


@app.command()
def eval_cmd(
    dataset: str = typer.Option("compare", "--dataset", help="'compare' (72 real trials) or 'known' (mock pairs)"),
    ablation: bool = typer.Option(True, "--ablation/--no-ablation", help="Include ablation study"),
):
    """Run systematic evaluation with per-constraint metrics.

    Default: COMPARE dataset (72 human-annotated trials from Goldacre et al. 2019).
    Use --dataset known for mock known-deviation pairs.

    Produces precision/recall/F1 per constraint, confusion matrix, and
    ablation table showing the contribution of each architectural component.
    """
    from evaluation import evaluate_dataset, load_compare_dataset, load_known_deviations
    from evaluation.compare_eval import format_compare_results, evaluate_compare_pipeline, load_compare_trials

    if dataset == "compare":
        trials = load_compare_trials()
        if not trials:
            console.print("[red]Could not load COMPARE dataset CSV.[/]")
            return

        console.print(f"[cyan]COMPARE Dataset: {len(trials)} human-annotated clinical trials[/]")
        console.print("[dim]Goldacre et al. (2019), Trials, 20(1), 118[/]")
        console.print("[dim]Evaluating comparison pipeline against real-world deviation patterns[/]\n")

        results = evaluate_compare_pipeline(trials)
        console.print(format_compare_results(results))

        # Summary for quick reading
        over = results["OVERALL"]
        console.print(f"\n[bold]Summary:[/]")
        console.print(f"  Overall F1: {over['f1']:.2f}  "
                     f"(P={over['precision']:.2f}, R={over['recall']:.2f})")
        console.print(f"  TP={over['tp']}, FP={over['fp']}, FN={over['fn']}")

        # C1 detail
        c1 = results["C1"]
        console.print(f"\n  [bold]C1 (Outcome Switching):[/] F1={c1['f1']:.2f} "
                     f"(TP={c1['tp']}, FP={c1['fp']}, FN={c1['fn']})")
        if c1['fp'] > 0:
            console.print(f"  [dim]→ {c1['fp']} false positives: constraint catches non-C1 deviations too[/]")
        if c1['fn'] > 0:
            console.print(f"  [dim]→ {c1['fn']} false negatives: primary outcome switches missed[/]")

    else:
        gt = load_known_deviations()
        console.print(f"  {len(gt)} ground-truth pairs loaded\n")
        report = evaluate_dataset(dataset=gt)
        console.print(report.summary_text)
        if report.overall_metrics:
            om = report.overall_metrics
            console.print(f"\n[bold]Overall Metrics:[/]")
            console.print(f"  Precision: {om.precision:.2f}  Recall: {om.recall:.2f}  F1: {om.f1:.2f}")

        console.print(report.per_constraint_table())

        if report.confusion_matrix:
            console.print("\n[bold]Confusion Matrix:[/]")
            console.print(report.confusion_matrix.to_text_table())

        if ablation and report.ablation_table:
            console.print("\n[bold]Ablation Study:[/]")
            table = report.ablation_table.to_rich_table()
            if table:
                console.print(table)
            else:
                console.print(report.ablation_table.to_markdown())
            console.print("\n[bold green]Interpretation:[/]")
            console.print(
                "  F1 degradation when disabling a component = that component's\n"
                "  independent contribution. Larger drops = more critical."
            )

        if report.errors:
            console.print(f"\n[red]{len(report.errors)} errors during evaluation[/]")
            for err in report.errors[:5]:
                console.print(f"  - {err}")


@app.command()
def compare(
    registration: str = typer.Argument(..., help="Path to registration PDF or markdown"),
    publication: str = typer.Argument(..., help="Path to publication PDF or markdown"),
    output: str = typer.Option("data/output", help="Output directory"),
    mock: bool = typer.Option(False, help="Use mock data instead of LLM extraction"),
):
    """Compare a registration against a publication."""
    from agents.workflow import VerificationWorkflow
    from demos.dashboard import run_dashboard
    from parsers import DoclingParser, MockParser, ParsedDocument
    from reports.ledger_generator import LedgerGenerator

    reg_path = Path(registration)
    pub_path = Path(publication)

    if mock:
        workflow = VerificationWorkflow()
        result = workflow.run(use_mock=True)
    else:
        parser = _get_parser(reg_path)
        console.print(f"[cyan]Parsing registration: {reg_path}[/]")
        reg_doc = parser.parse(reg_path)

        parser = _get_parser(pub_path)
        console.print(f"[cyan]Parsing publication: {pub_path}[/]")
        pub_doc = parser.parse(pub_path)

        workflow = VerificationWorkflow()
        result = workflow.run(
            registration_doc=reg_doc,
            publication_doc=pub_doc,
            use_mock=False,
        )

    ledger = result["audit_ledger"]
    if ledger:
        run_dashboard(ledger)

        generator = LedgerGenerator()
        md_report = generator.render_markdown(ledger)

        output_dir = Path(output)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "audit_report.md"
        report_path.write_text(md_report, encoding="utf-8")
        console.print(f"\n[dim]Report saved to: {report_path}[/]")

        json_path = output_dir / "audit_report.json"
        json_path.write_text(
            ledger.model_dump_json(indent=2), encoding="utf-8"
        )
        console.print(f"[dim]JSON saved to: {json_path}[/]")
    else:
        console.print("[red]Error: No audit ledger generated.[/]")
        if result.get("errors"):
            for err in result["errors"]:
                console.print(f"  [red]- {err}[/]")
        sys.exit(1)


@app.command()
def schema():
    """Display the ScientificContract JSON schema."""
    from schemas.ir import ScientificContract
    from rich.syntax import Syntax

    schema = ScientificContract.model_json_schema()
    json_str = json.dumps(schema, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(syntax)


@app.command()
def demo():
    """Run a demonstration with mock data (no LLM or PDFs needed)."""
    from agents.workflow import VerificationWorkflow
    from demos.dashboard import run_dashboard
    from reports.ledger_generator import LedgerGenerator

    console.print("[cyan]Starting RegCheck v1.1 demo with mock data...[/]\n")

    workflow = VerificationWorkflow()
    result = workflow.run(use_mock=True)

    ledger = result["audit_ledger"]
    if ledger:
        run_dashboard(ledger)

        generator = LedgerGenerator()
        md_report = generator.render_markdown(ledger)

        output_dir = Path("data/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "demo_report.md"
        report_path.write_text(md_report, encoding="utf-8")
        console.print(f"\n[dim]Report saved to: {report_path}[/]")
    else:
        console.print("[red]Error: No audit ledger generated.[/]")
        sys.exit(1)


def _get_parser(source: Path):
    """Select the best parser for a given source.

    Parser selection logic:
        .json → CTGovJSONParser (for ClinicalTrials.gov structured data)
        .pdf/.docx → DoclingParser (layout-aware parsing)
        .md → MockParser (passthrough for pre-parsed markdown)
        fallback → MockParser
    """
    from parsers import CTGovJSONParser, DoclingParser, MockParser

    suffix = source.suffix.lower()

    if suffix == ".json":
        ctp = CTGovJSONParser()
        if ctp.supports(source):
            return ctp
        return MockParser()

    if suffix in (".md",):
        return MockParser()

    if suffix in (".pdf", ".docx"):
        try:
            parser = DoclingParser()
            if parser.supports(source):
                return parser
        except ImportError:
            console.print(
                "[yellow]Docling not available, falling back to MockParser[/]"
            )

    return MockParser()


if __name__ == "__main__":
    app()
