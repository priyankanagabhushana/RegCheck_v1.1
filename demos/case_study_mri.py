"""MRI/ML Case Study — Demonstrates domain-specific constraint plugins.

Shows how the Scientific Integrity Engine catches deviations in
computational imaging pipelines that generic text comparison would miss.

Scenario: A neuroimaging study pre-registered specific MRI sequence parameters,
cross-vendor robustness checks, and physics-informed UQ — then silently dropped
or altered them in the publication.

Usage:
    python demos/case_study_mri.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from compilers.constraint_engine import ConstraintEngine
from graph.graph_builder import ProtocolGraphBuilder
from graph.graph_differ import GraphDiffer
from reports.ledger_generator import LedgerGenerator
from reports.severity_scorer import SeverityScorer
from schemas.ir import (
    DomainSpecificParameters,
    ExclusionCriterion,
    Hypothesis,
    HypothesisType,
    MRIParameters,
    Outcome,
    OutcomeType,
    SampleSize,
    ScientificAnalysis as StatisticalAnalysis,
    ScientificClaim,
    ScientificContract,
    UncertaintyFlag,
)

console = Console()


def build_mri_registration() -> ScientificContract:
    """Pre-registration for an fMRI study on working memory.

    Pre-registered on OSF: specific scanner parameters, preprocessing pipeline,
    cross-vendor robustness checks, and physics-informed uncertainty quantification.
    """
    return ScientificContract(
        doc_id="OSF_2026_MRI_reg",
        doc_type="registration",
        title="Functional Connectivity Predicts Working Memory Performance: A Multi-Site fMRI Study",
        authors=["Zhang, L.", "Patel, R.", "Kim, S."],
        registration_id="osf.io/abc123",
        hypotheses=[
            Hypothesis(
                id="H1",
                description="DLPFC-PPC functional connectivity strength will positively predict working memory accuracy",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=["DLPFC_PPC_connectivity", "WM_accuracy"],
                direction="greater",
            ),
            Hypothesis(
                id="H2",
                description="Connectivity-behavior relationships will be consistent across Siemens and GE scanners",
                hypothesis_type=HypothesisType.SECONDARY,
                variables=["cross_vendor_consistency"],
            ),
        ],
        outcomes=[
            Outcome(
                id="O1",
                measure="DLPFC-PPC functional connectivity (Fisher z-transformed)",
                timepoint="baseline scan",
                outcome_type=OutcomeType.PRIMARY,
            ),
            Outcome(
                id="O2",
                measure="N-back task accuracy (2-back condition)",
                timepoint="in-scanner",
                outcome_type=OutcomeType.PRIMARY,
            ),
        ],
        sample_size=SampleSize(
            planned_n=120,
            power_analysis="Power=0.85, alpha=0.05, r=0.30, two-tailed",
            dropout_rate=0.10,
        ),
        exclusion_criteria=[
            ExclusionCriterion(id="E1", description="Head motion > 3mm translation or 3° rotation", criterion_type="exclusion"),
            ExclusionCriterion(id="E2", description="History of neurological or psychiatric disorder", criterion_type="exclusion"),
            ExclusionCriterion(id="E3", description="Contraindications for MRI", criterion_type="exclusion"),
        ],
        analyses=[
            StatisticalAnalysis(
                id="SA1",
                model="Mixed-effects regression",
                dependent_variable="WM_accuracy",
                independent_variables=["connectivity", "scanner_vendor", "age", "sex"],
                covariates=["site", "head_motion_fd"],
                software="FSL 6.0 + Python Nilearn",
            ),
            StatisticalAnalysis(
                id="SA2",
                model="Permutation testing (5000 permutations)",
                dependent_variable="connectivity-behavior correlation",
                corrections=["FDR correction (q<0.05)"],
            ),
        ],
        claims=[],
        domain_params=DomainSpecificParameters(
            mri=MRIParameters(
                scanner_field_strength=3.0,
                tr_ms=2000,
                te_ms=30,
                voxel_size_mm=[2.0, 2.0, 2.0],
                sequence_type="Gradient-echo EPI (fMRI BOLD)",
                region_of_interest="DLPFC and PPC (bilateral)",
                preprocessing_pipeline="fMRIPrep 23.1.0 + ICA-AROMA denoising",
                cross_vendor_checks=True,
                uncertainty_quantification="Bootstrap confidence intervals (1000 resamples) + physics-informed signal-to-noise estimation",
            ),
        ),
    )


def build_mri_publication() -> ScientificContract:
    """Publication with subtle MRI-specific deviations.

    Deviations injected (all text-similarity would miss):
    1. TR changed: 2000ms → 1500ms (faster scanning, different SNR characteristics)
    2. Cross-vendor checks silently dropped
    3. UQ method changed from bootstrap+physics to just p-values
    4. Preprocessing changed: fMRIPrep+ICA-AROMA → just fMRIPrep (no denoising)
    5. Added exclusion criterion E4 (post-hoc motion threshold change)
    6. Claim about cross-vendor consistency not backed by H2
    """
    return ScientificContract(
        doc_id="OSF_2026_MRI_pub",
        doc_type="publication",
        title="Functional Connectivity Predicts Working Memory Performance: A Multi-Site fMRI Study",
        authors=["Zhang, L.", "Patel, R.", "Kim, S.", "Liu, W."],
        doi="10.1000/neuro.2026.5678",
        registration_id="osf.io/abc123",
        hypotheses=[
            Hypothesis(
                id="H1",
                description="DLPFC-PPC functional connectivity strength will positively predict working memory accuracy",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=["DLPFC_PPC_connectivity", "WM_accuracy"],
                direction="greater",
            ),
        ],
        outcomes=[
            Outcome(
                id="O1",
                measure="DLPFC-PPC functional connectivity (Fisher z-transformed)",
                timepoint="baseline scan",
                outcome_type=OutcomeType.PRIMARY,
            ),
            Outcome(
                id="O2",
                measure="N-back task accuracy (2-back condition)",
                timepoint="in-scanner",
                outcome_type=OutcomeType.PRIMARY,
            ),
        ],
        sample_size=SampleSize(
            planned_n=120,
            actual_n=98,
            dropout_rate=0.183,
        ),
        exclusion_criteria=[
            ExclusionCriterion(id="E1", description="Head motion > 2mm translation or 2° rotation", criterion_type="exclusion"),
            ExclusionCriterion(id="E2", description="History of neurological or psychiatric disorder", criterion_type="exclusion"),
            ExclusionCriterion(id="E3", description="Contraindications for MRI", criterion_type="exclusion"),
            ExclusionCriterion(id="E4", description="Excessive signal dropout in frontal regions", criterion_type="exclusion"),
        ],
        analyses=[
            StatisticalAnalysis(
                id="SA1",
                model="Mixed-effects regression",
                dependent_variable="WM_accuracy",
                independent_variables=["connectivity", "age", "sex"],
                covariates=["site"],
                software="FSL 6.0 + Python Nilearn",
            ),
        ],
        claims=[
            ScientificClaim(
                id="C1",
                text="Functional connectivity is a robust biomarker of working memory that generalizes across scanner manufacturers",
                mapped_hypothesis_id="H1",
                mapped_outcome_ids=["O1", "O2"],
                strength="supported",
            ),
        ],
        domain_params=DomainSpecificParameters(
            mri=MRIParameters(
                scanner_field_strength=3.0,
                tr_ms=1500,
                te_ms=30,
                voxel_size_mm=[2.0, 2.0, 2.0],
                sequence_type="Gradient-echo EPI (fMRI BOLD)",
                region_of_interest="DLPFC and PPC (bilateral)",
                preprocessing_pipeline="fMRIPrep 23.1.0",
                cross_vendor_checks=False,
                uncertainty_quantification="p-values with FDR correction",
            ),
        ),
    )


def run_mri_case_study():
    """Run the MRI case study and display results."""
    console.clear()

    console.print(Panel(
        "[bold cyan]RegCheck v1.1 — MRI/ML Case Study[/]\n"
        "[dim]Domain-specific constraint plugins catching deviations in computational imaging[/]\n\n"
        "[bold]Scenario:[/] Multi-site fMRI study on working memory\n"
        "Pre-registered on OSF with specific scanner parameters and robustness checks",
        border_style="cyan",
    ))

    reg_contract = build_mri_registration()
    pub_contract = build_mri_publication()

    builder = ProtocolGraphBuilder()
    reg_graph = builder.build(reg_contract)
    pub_graph = builder.build(pub_contract)

    # Add MRI params as graph nodes for domain constraints
    _add_mri_graph_nodes(reg_graph, reg_contract)
    _add_mri_graph_nodes(pub_graph, pub_contract)

    differ = GraphDiffer()
    mutations = differ.diff(reg_graph, pub_graph)

    # Use the pluggable constraint engine (MRI constraints auto-loaded)
    engine = ConstraintEngine(load_core=True, load_domain=True)
    constraint_results = engine.evaluate_all(reg_graph, pub_graph)

    scorer = SeverityScorer()
    all_deviations = engine.violations_to_deviations(constraint_results)
    for mutation in mutations:
        dev = scorer.score_mutation(mutation)
        if dev:
            all_deviations.append(dev)

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

    _show_mri_deviations(ledger, constraint_results)
    _show_domain_plugin_demo(engine)
    _show_what_text_similarity_misses_mri()
    _show_mri_parameters_comparison(reg_contract, pub_contract)

    md_report = generator.render_markdown(ledger)
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "mri_case_study_report.md"
    report_path.write_text(md_report, encoding="utf-8")
    console.print(f"\n[dim]Full report saved to: {report_path}[/]")


def _add_mri_graph_nodes(graph, contract):
    """Add MRI parameters as graph nodes for domain constraint checking."""
    if contract.domain_params.mri:
        mri = contract.domain_params.mri
        graph.add_node(
            "mri_params",
            node_type="mri_parameters",
            label="MRI Scanner Parameters",
            tr_ms=mri.tr_ms,
            te_ms=mri.te_ms,
            scanner_field_strength=mri.scanner_field_strength,
            sequence_type=mri.sequence_type,
            preprocessing_pipeline=mri.preprocessing_pipeline,
            cross_vendor_checks=mri.cross_vendor_checks,
            uncertainty_quantification=mri.uncertainty_quantification,
            doc_id=contract.doc_id,
        )


def _show_mri_deviations(ledger, constraint_results):
    """Show MRI-specific deviations."""
    console.print("\n")
    console.print(Panel(
        "[bold red]MRI-SPECIFIC DEVIATIONS DETECTED[/]\n"
        "[dim]These require domain expertise to catch — generic text comparison would miss them:[/]",
        border_style="red",
    ))

    table = Table(show_lines=True)
    table.add_column("#", width=3)
    table.add_column("Constraint", max_width=25)
    table.add_column("Status", width=10)
    table.add_column("Detail", max_width=50)

    for i, r in enumerate(constraint_results, 1):
        if r.status.value in ("violated", "uncertain"):
            status_style = "[red]VIOLATED[/]" if r.status.value == "violated" else "[yellow]UNCERTAIN[/]"
            table.add_row(str(i), r.constraint_name, status_style, r.violation_detail or "")

    console.print(table)


def _show_domain_plugin_demo(engine):
    """Show the pluggable constraint architecture."""
    console.print("\n")
    constraints = engine.list_constraints()

    tree = Tree("[bold]Registered Constraint Plugins[/]")
    core = tree.add("[cyan]Core Constraints (always loaded)[/]")
    domain = tree.add("[magenta]Domain Plugins (MRI)[/]")

    for c in constraints:
        if c["id"].startswith("MRI"):
            domain.add(f"[{c['id']}] {c['name']}")
        else:
            core.add(f"[{c['id']}] {c['name']}")

    console.print(tree)


def _show_what_text_similarity_misses_mri():
    """Show why text similarity fails for MRI parameters."""
    console.print("\n")
    console.print(Panel(
        "[bold]WHY TEXT SIMILARITY FAILS FOR MRI[/]\n\n"
        "[bold red]TR=2000ms vs TR=1500ms[/]\n"
        "  Both appear in a 'Methods' section about MRI acquisition.\n"
        "  Cosine similarity: ~0.95 (nearly identical text blocks)\n"
        "  But TR change alters SNR, temporal resolution, and BOLD signal characteristics.\n"
        "  → Constraint MRI-C1 catches this as a parameter change.\n\n"
        "[bold red]Cross-vendor checks: True → False[/]\n"
        "  Registration says 'cross-vendor robustness verified'.\n"
        "  Publication silently drops this.\n"
        "  Text similarity can't detect a boolean field change.\n"
        "  → Constraint MRI-C2 catches this as a reporting gap.\n\n"
        "[bold red]UQ method: Bootstrap+physics → just p-values[/]\n"
        "  Both mention 'statistical analysis'.\n"
        "  But the registered method was more rigorous.\n"
        "  → The typed field comparison detects the downgrade.",
        border_style="yellow",
    ))


def _show_mri_parameters_comparison(reg_contract, pub_contract):
    """Side-by-side MRI parameters comparison."""
    console.print("\n")
    table = Table(title="MRI Parameters: Registration vs Publication")
    table.add_column("Parameter")
    table.add_column("Registration", style="green")
    table.add_column("Publication", style="red")
    table.add_column("Match")

    reg_mri = reg_contract.domain_params.mri
    pub_mri = pub_contract.domain_params.mri

    params = [
        ("Field Strength (T)", reg_mri.scanner_field_strength, pub_mri.scanner_field_strength),
        ("TR (ms)", reg_mri.tr_ms, pub_mri.tr_ms),
        ("TE (ms)", reg_mri.te_ms, pub_mri.te_ms),
        ("Sequence", reg_mri.sequence_type, pub_mri.sequence_type),
        ("Preprocessing", reg_mri.preprocessing_pipeline, pub_mri.preprocessing_pipeline),
        ("Cross-Vendor", reg_mri.cross_vendor_checks, pub_mri.cross_vendor_checks),
        ("UQ Method", reg_mri.uncertainty_quantification, pub_mri.uncertainty_quantification),
    ]

    for name, reg_val, pub_val in params:
        match = "[green]✓[/]" if str(reg_val) == str(pub_val) else "[red]✗[/]"
        table.add_row(name, str(reg_val or "N/A"), str(pub_val or "N/A"), match)

    console.print(table)


if __name__ == "__main__":
    run_mri_case_study()
