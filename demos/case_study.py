"""Case Study Demo — Catches subtle protocol deviations that text similarity would miss.

This demonstrates the paradigm shift: from "text chunks look similar" to
"typed fields in structured models must be identical."

Usage:
    python demos/case_study.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from agents.workflow import VerificationWorkflow
from compilers.contract_extractor import create_mock_contract
from graph.graph_builder import ProtocolGraphBuilder
from graph.graph_differ import GraphDiffer
from compilers.constraint_engine import ConstraintEngine
from reports.ledger_generator import LedgerGenerator
from reports.severity_scorer import SeverityScorer
from schemas.ir import (
    BiasRisk,
    ConfidenceLevel,
    DomainSpecificParameters,
    EvidenceGraph,
    EvidenceNode,
    EvidenceNodeType,
    EvidenceSpan,
    ExclusionCriterion,
    Hypothesis,
    HypothesisType,
    MultiAxisSeverity,
    Outcome,
    OutcomeType,
    SampleSize,
    ScientificAnalysis as StatisticalAnalysis,
    ScientificClaim,
    ScientificContract,
    UncertaintyFlag,
)

console = Console()


def build_clinical_trial_registration() -> ScientificContract:
    """Build a realistic clinical trial registration (Protocol IR)."""
    return ScientificContract(
        doc_id="NCT04123456_reg",
        doc_type="registration",
        title="Efficacy of Cognitive Behavioral Therapy for Generalized Anxiety Disorder: A Randomized Controlled Trial",
        authors=["Smith, J.", "Johnson, A.", "Williams, R."],
        registration_id="NCT04123456",
        hypotheses=[
            Hypothesis(
                id="H1",
                description="CBT will reduce anxiety symptoms by at least 30% compared to waitlist control at 12 weeks",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=["anxiety_symptoms", "CBT", "waitlist_control"],
                direction="greater",
            ),
            Hypothesis(
                id="H2",
                description="CBT effects will persist at 6-month follow-up assessment",
                hypothesis_type=HypothesisType.SECONDARY,
                variables=["anxiety_symptoms", "follow_up"],
            ),
            Hypothesis(
                id="H3",
                description="CBT will improve sleep quality as measured by PSQI",
                hypothesis_type=HypothesisType.SECONDARY,
                variables=["sleep_quality", "PSQI"],
            ),
        ],
        outcomes=[
            Outcome(
                id="O1",
                measure="GAD-7 Anxiety Scale",
                timepoint="12 weeks post-randomization",
                outcome_type=OutcomeType.PRIMARY,
                description="7-item self-report measure of generalized anxiety",
            ),
            Outcome(
                id="O2",
                measure="PHQ-9 Depression Scale",
                timepoint="12 weeks post-randomization",
                outcome_type=OutcomeType.SECONDARY,
                description="9-item self-report measure of depression severity",
            ),
            Outcome(
                id="O3",
                measure="Pittsburgh Sleep Quality Index (PSQI)",
                timepoint="12 weeks post-randomization",
                outcome_type=OutcomeType.SECONDARY,
            ),
        ],
        sample_size=SampleSize(
            planned_n=200,
            power_analysis="Power=0.80, alpha=0.05, effect size d=0.5, two-tailed",
            dropout_rate=0.15,
            justification="Based on prior meta-analysis of CBT for GAD (Cuijpers et al., 2016)",
        ),
        exclusion_criteria=[
            ExclusionCriterion(id="E1", description="Current suicidal ideation (PHQ-9 item 9 >= 2)", criterion_type="exclusion"),
            ExclusionCriterion(id="E2", description="Concurrent psychotherapy", criterion_type="exclusion"),
            ExclusionCriterion(id="E3", description="Changes in psychotropic medication within past 4 weeks", criterion_type="exclusion"),
            ExclusionCriterion(id="E4", description="Primary diagnosis of substance use disorder", criterion_type="exclusion"),
        ],
        analyses=[
            StatisticalAnalysis(
                id="SA1",
                model="ANCOVA",
                dependent_variable="GAD-7 post-treatment",
                covariates=["GAD-7 baseline", "age", "gender", "medication_status"],
                corrections=["Bonferroni"],
                software="R 4.3.0",
            ),
            StatisticalAnalysis(
                id="SA2",
                model="Mixed-effects model",
                dependent_variable="GAD-7 trajectory",
                independent_variables=["time", "group", "time x group"],
                covariates=["GAD-7 baseline"],
            ),
        ],
        domain_params=DomainSpecificParameters(),
    )


def build_publication_with_deviations() -> ScientificContract:
    """Build a publication with SUBTLE deviations that text similarity would miss.

    Deviations injected:
    1. Primary outcome changed: GAD-7 → STAI (both anxiety measures, high cosine similarity)
    2. Analysis model downgraded: ANCOVA → t-test (simpler, less control)
    3. Exclusion criterion E3 dropped (medication changes no longer excluded)
    4. Sample size: N=200 planned → N=147 reported (26.5% dropout, not documented)
    5. New hypothesis H4 added post-hoc (not in registration)
    6. Claim C1 not traceable to any registered hypothesis
    """
    return ScientificContract(
        doc_id="NCT04123456_pub",
        doc_type="publication",
        title="Efficacy of Cognitive Behavioral Therapy for Generalized Anxiety Disorder: A Randomized Controlled Trial",
        authors=["Smith, J.", "Johnson, A.", "Williams, R.", "Chen, L."],
        doi="10.1001/example.2026.1234",
        registration_id="NCT04123456",
        hypotheses=[
            Hypothesis(
                id="H1",
                description="CBT will reduce anxiety symptoms compared to waitlist control at 12 weeks",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=["anxiety_symptoms", "CBT"],
                direction="greater",
            ),
            Hypothesis(
                id="H2",
                description="CBT effects will persist at 6-month follow-up assessment",
                hypothesis_type=HypothesisType.SECONDARY,
            ),
            Hypothesis(
                id="H4",
                description="CBT will reduce rumination as measured by RRS",
                hypothesis_type=HypothesisType.EXPLORATORY,
                variables=["rumination", "RRS"],
            ),
        ],
        outcomes=[
            Outcome(
                id="O1",
                measure="State-Trait Anxiety Inventory (STAI)",
                timepoint="12 weeks post-randomization",
                outcome_type=OutcomeType.PRIMARY,
                description="20-item self-report measure of state and trait anxiety",
            ),
            Outcome(
                id="O2",
                measure="PHQ-9 Depression Scale",
                timepoint="12 weeks post-randomization",
                outcome_type=OutcomeType.SECONDARY,
            ),
            Outcome(
                id="O3",
                measure="Pittsburgh Sleep Quality Index (PSQI)",
                timepoint="12 weeks post-randomization",
                outcome_type=OutcomeType.SECONDARY,
            ),
        ],
        sample_size=SampleSize(
            planned_n=200,
            actual_n=147,
            dropout_rate=0.265,
        ),
        exclusion_criteria=[
            ExclusionCriterion(id="E1", description="Current suicidal ideation (PHQ-9 item 9 >= 2)", criterion_type="exclusion"),
            ExclusionCriterion(id="E2", description="Concurrent psychotherapy", criterion_type="exclusion"),
            ExclusionCriterion(id="E4", description="Primary diagnosis of substance use disorder", criterion_type="exclusion"),
        ],
        analyses=[
            StatisticalAnalysis(
                id="SA1",
                model="Independent samples t-test",
                dependent_variable="STAI change score",
                software="SPSS 28",
            ),
        ],
        claims=[
            ScientificClaim(
                id="C1",
                text="CBT is an effective treatment for reducing rumination in GAD patients",
                mapped_hypothesis_id="H4",
                strength="supported",
            ),
        ],
        domain_params=DomainSpecificParameters(),
    )


def run_case_study():
    """Run the case study and display results."""
    console.clear()

    console.print(Panel(
        "[bold cyan]RegCheck v1.1 — Case Study Demo[/]\n"
        "[dim]Catching subtle protocol deviations that text similarity would miss[/]\n\n"
        "[bold]Scenario:[/] Clinical trial NCT04123456\n"
        "CBT for Generalized Anxiety Disorder — RCT",
        border_style="cyan",
    ))

    # Build the contracts
    reg_contract = build_clinical_trial_registration()
    pub_contract = build_publication_with_deviations()

    # Build graphs
    builder = ProtocolGraphBuilder()
    reg_graph = builder.build(reg_contract)
    pub_graph = builder.build(pub_contract)

    # Run graph diff
    differ = GraphDiffer()
    mutations = differ.diff(reg_graph, pub_graph)

    # Run constraint engine
    engine = ConstraintEngine()
    constraint_results = engine.evaluate_all(reg_graph, pub_graph)

    # Score all deviations
    scorer = SeverityScorer()
    all_deviations = []

    for result in constraint_results:
        if result.status.value in ("violated", "uncertain"):
            dev = engine.violations_to_deviations([result])
            all_deviations.extend(dev)

    for mutation in mutations:
        dev = scorer.score_mutation(mutation)
        if dev:
            all_deviations.append(dev)

    # Generate report
    generator = LedgerGenerator()
    ledger = generator.generate(
        registration_contract=reg_contract,
        publication_contract=pub_contract,
        deviations=all_deviations,
        constraint_violations=[
            r.violation_detail or r.description
            for r in constraint_results if r.status.value == "violated"
        ],
        graph_mutations=mutations,
    )

    # Display
    _show_deviation_analysis(ledger)
    _show_what_text_similarity_misses()
    _show_claim_provenance(pub_contract)
    _show_graph_comparison(reg_graph, pub_graph)

    # Save report
    md_report = generator.render_markdown(ledger)
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "case_study_report.md"
    report_path.write_text(md_report, encoding="utf-8")
    console.print(f"\n[dim]Full report saved to: {report_path}[/]")


def _show_deviation_analysis(ledger):
    """Show the deviations with emphasis on what text similarity would miss."""
    console.print("\n")
    console.print(Panel(
        "[bold red]DEVIATIONS DETECTED[/]\n"
        "[dim]These are deviations that cosine similarity on text chunks would likely miss:[/]",
        border_style="red",
    ))

    table = Table(show_lines=True)
    table.add_column("#", width=3)
    table.add_column("Deviation", max_width=30)
    table.add_column("Why Text Similarity Fails", max_width=35)
    table.add_column("Sev", width=4)
    table.add_column("Bias", width=10)

    critical = [
        d for d in ledger.deviations
        if d.severity.value >= "S4"
    ]

    for i, dev in enumerate(critical, 1):
        why = _explain_why_text_similarity_fails(dev)
        table.add_row(
            str(i),
            dev.description[:80],
            why,
            f"[bold red]{dev.severity.value}[/]",
            f"[red]{dev.multi_axis.bias_risk.value}[/]",
        )

    console.print(table)


def _explain_why_text_similarity_fails(dev) -> str:
    """Explain why text similarity would miss this deviation."""
    if "outcome" in dev.category.lower() or "GAD" in dev.description:
        return (
            "GAD-7 and STAI are both anxiety measures. "
            "Cosine similarity would rate them as highly similar. "
            "The constraint engine checks the typed 'measure' field."
        )
    if "analysis" in dev.category.lower() or "ANCOVA" in dev.description:
        return (
            "ANCOVA and t-test both test group differences. "
            "Similar wording in methods section. "
            "The graph diff detects the 'model' attribute change."
        )
    if "sample" in dev.category.lower():
        return (
            "N=200 vs N=147 is a 26.5% drop. "
            "Text would show both numbers but wouldn't "
            "compute the constraint: N_actual >= N_planned * 0.5."
        )
    if "hypothesis" in dev.category.lower():
        return (
            "Hypothesis H4 was added post-hoc. "
            "Text similarity can't detect that this hypothesis "
            "doesn't exist in the registration."
        )
    return "Structural comparison detects what text similarity cannot."


def _show_what_text_similarity_misses():
    """Show a concrete example of the paradigm shift."""
    console.print("\n")
    console.print(Panel(
        "[bold]THE PARADIGM SHIFT[/]\n\n"
        "[bold red]Text Similarity:[/]\n"
        '  Registration: "Primary outcome: GAD-7 Anxiety Scale"\n'
        '  Publication:  "Primary outcome: State-Trait Anxiety Inventory (STAI)"\n'
        "  → Cosine similarity: 0.72 (HIGH — both mention anxiety)\n"
        "  → Verdict: No deviation detected\n\n"
        "[bold green]Constraint Engine:[/]\n"
        "  Registration O1.measure = 'GAD-7 Anxiety Scale'\n"
        "  Publication  O1.measure = 'State-Trait Anxiety Inventory (STAI)'\n"
        "  → Constraint C1: Primary outcome must be identical\n"
        "  → Verdict: S5 BIAS-CRITICAL — Outcome switched\n\n"
        "[dim]The difference: one compares text embeddings, the other compares typed fields.[/]",
        border_style="yellow",
    ))


def _show_claim_provenance(contract: ScientificContract):
    """Show the claim provenance chain."""
    console.print("\n")
    console.print(Panel("[bold]CLAIM PROVENANCE CHAIN[/]", border_style="blue"))

    tree = Tree("[bold]Publication Claims → Evidence → Protocol[/]")

    for claim in contract.claims:
        chain = claim.provenance_chain()
        claim_branch = tree.add(
            f"[bold]{claim.id}[/]: {claim.text[:60]}..."
        )

        if chain["hypothesis"]:
            claim_branch.add(f"Mapped to hypothesis: [cyan]{chain['hypothesis']}[/]")
        else:
            claim_branch.add("[red]NO REGISTERED HYPOTHESIS — post-hoc claim[/]")

        if chain["outcomes"]:
            claim_branch.add(f"Supporting outcomes: {chain['outcomes']}")
        else:
            claim_branch.add("[yellow]No linked outcomes[/]")

        if claim.uncertainty.is_uncertain:
            claim_branch.add(f"[red]UNCERTAIN: {claim.uncertainty.reason}[/]")

    console.print(tree)


def _show_graph_comparison(reg_graph, pub_graph):
    """Show the structural graph comparison."""
    console.print("\n")
    console.print(Panel("[bold]PROTOCOL GRAPH COMPARISON[/]", border_style="dim"))

    reg_summary = ProtocolGraphBuilder.get_graph_summary(reg_graph)
    pub_summary = ProtocolGraphBuilder.get_graph_summary(pub_graph)

    table = Table(title="Graph Statistics")
    table.add_column("Metric")
    table.add_column("Registration (Protocol IR)")
    table.add_column("Publication (Execution IR)")

    table.add_row("Nodes", str(reg_summary["node_count"]), str(pub_summary["node_count"]))
    table.add_row("Edges", str(reg_summary["edge_count"]), str(pub_summary["edge_count"]))

    for ntype in ("hypothesis", "outcome", "analysis", "parameter", "exclusion_criterion"):
        reg_count = reg_summary["node_types"].get(ntype, 0)
        pub_count = pub_summary["node_types"].get(ntype, 0)
        style = "red" if reg_count != pub_count else "green"
        table.add_row(
            ntype.replace("_", " ").title(),
            str(reg_count),
            f"[{style}]{pub_count}[/]",
        )

    console.print(table)


if __name__ == "__main__":
    run_case_study()
