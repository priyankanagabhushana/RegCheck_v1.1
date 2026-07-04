"""LangGraph Multi-Agent Verification Workflow.

State machine with nodes:
- ContractExtractor: Compiles documents into ScientificContract IR
- GraphDiffNode: Builds graphs and runs structural + semantic differencing
- ConstraintEngine: Formal constraint satisfaction (6 core + domain plugins)
- CriticAgent: Self-reflects on deviations, flags false positives, handles uncertainty
- ReportGenerator: Compiles final AuditLedger

Supports three input modes:
    - PDF registration + PDF publication (standard)
    - CT.gov JSON registration + PDF publication (structured registration)
    - PDF amendment v1 + PDF amendment v2 (version comparison)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from compilers.constraint_engine import ConstraintEngine
from compilers.contract_extractor import ContractExtractor, create_mock_contract
from graph.graph_builder import ProtocolGraphBuilder
from graph.graph_differ import GraphDiffer
from parsers.base import ParsedDocument
from reports.ledger_generator import LedgerGenerator
from reports.severity_scorer import SeverityScorer
from schemas.ir import AuditLedger, Deviation, DeviationSeverity, ScientificContract

logger = logging.getLogger(__name__)


# --- State ---

class WorkflowState(TypedDict):
    """State shared across all agent nodes."""
    registration_doc: Optional[ParsedDocument]
    publication_doc: Optional[ParsedDocument]
    registration_contract: Optional[ScientificContract]
    publication_contract: Optional[ScientificContract]
    registration_graph: Optional[Any]  # nx.DiGraph
    publication_graph: Optional[Any]  # nx.DiGraph
    graph_mutations: list  # list[GraphMutation]
    constraint_results: list  # list[ConstraintResult]
    deviations: list[Deviation]
    audit_ledger: Optional[AuditLedger]
    errors: list[str]
    use_mock: bool
    model: Optional[str]  # Configurable LLM model for extraction


# --- Node Functions ---

def contract_extractor_node(state: WorkflowState) -> dict:
    """Extract ScientificContracts from both documents.

    Processes registration and publication in parallel when both documents
    are available and LLM extraction is needed.
    """
    logger.info("=== Contract Extractor Node ===")
    errors = list(state.get("errors", []))
    use_mock = state.get("use_mock", False)
    model = state.get("model")

    if use_mock:
        logger.info("Using mock contracts (use_mock=True)")
        reg_contract = create_mock_contract("mock_registration", "registration")
        pub_contract = create_mock_contract("mock_publication", "publication")
        # Simulate deviations in the mock publication
        pub_contract.sample_size.actual_n = 150
        pub_contract.analyses[0].model = "t-test"
        pub_contract.outcomes[0].measure = "STAI Anxiety Scale"
    else:
        extractor_kwargs = {}
        if model:
            extractor_kwargs["model"] = model
        extractor = ContractExtractor(**extractor_kwargs)
        reg_doc = state["registration_doc"]
        pub_doc = state["publication_doc"]

        # Extract in parallel when both documents use LLM extraction
        if reg_doc and pub_doc and _needs_llm_extraction(reg_doc) and _needs_llm_extraction(pub_doc):
            reg_contract, pub_contract = _extract_parallel(
                extractor, reg_doc, pub_doc, errors
            )
        else:
            reg_contract = _safe_extract(
                extractor, reg_doc, "registration", errors,
                create_mock_contract("fallback_registration", "registration")
            )
            pub_contract = _safe_extract(
                extractor, pub_doc, "publication", errors,
                create_mock_contract("fallback_publication", "publication")
            )

    return {
        "registration_contract": reg_contract,
        "publication_contract": pub_contract,
        "errors": errors,
    }


def _needs_llm_extraction(doc: ParsedDocument) -> bool:
    return doc.parser_name not in ("ctgov_json", "mock")


def _safe_extract(
    extractor: ContractExtractor,
    doc: Optional[ParsedDocument],
    doc_type: str,
    errors: list[str],
    fallback: ScientificContract,
) -> ScientificContract:
    if doc is None:
        errors.append(f"No {doc_type} document provided")
        return fallback
    try:
        return extractor.extract(doc, doc_type=doc_type)
    except Exception as e:
        logger.error(f"{doc_type.title()} extraction failed: {e}")
        errors.append(f"{doc_type.title()} extraction error: {e}")
        return fallback


def _extract_parallel(
    extractor: ContractExtractor,
    reg_doc: ParsedDocument,
    pub_doc: ParsedDocument,
    errors: list[str],
) -> tuple[ScientificContract, ScientificContract]:
    """Run registration and publication extraction in parallel."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            raise RuntimeError("event loop running")
    except RuntimeError:
        pass

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            reg_future = executor.submit(extractor.extract, reg_doc, "registration")
            pub_future = executor.submit(extractor.extract, pub_doc, "publication")
            reg_contract = _future_or_fallback(reg_future, "registration", errors)
            pub_contract = _future_or_fallback(pub_future, "publication", errors)
        return reg_contract, pub_contract
    except Exception as e:
        logger.warning(f"Parallel extraction failed, falling back to sequential: {e}")
        reg_contract = _safe_extract(
            extractor, reg_doc, "registration", errors,
            create_mock_contract("fallback_registration", "registration")
        )
        pub_contract = _safe_extract(
            extractor, pub_doc, "publication", errors,
            create_mock_contract("fallback_publication", "publication")
        )
        return reg_contract, pub_contract


def _future_or_fallback(future, doc_type: str, errors: list[str]) -> ScientificContract:
    try:
        return future.result(timeout=120)
    except Exception as e:
        logger.error(f"Parallel {doc_type} extraction failed: {e}")
        errors.append(f"Parallel {doc_type} extraction error: {e}")
        return create_mock_contract(f"fallback_{doc_type}", doc_type)


def graph_diff_node(state: WorkflowState) -> dict:
    """Build protocol graphs and compute structural + semantic diff."""
    logger.info("=== Graph Diff Node ===")

    reg_contract = state["registration_contract"]
    pub_contract = state["publication_contract"]

    builder = ProtocolGraphBuilder()
    reg_graph = builder.build(reg_contract)
    pub_graph = builder.build(pub_contract)

    differ = GraphDiffer()
    mutations = differ.diff(reg_graph, pub_graph)

    semantic_count = sum(1 for m in mutations if m.is_semantic)
    logger.info(
        f"Graph diff: {len(mutations)} mutations ({semantic_count} semantic)"
    )

    return {
        "registration_graph": reg_graph,
        "publication_graph": pub_graph,
        "graph_mutations": mutations,
    }


def constraint_engine_node(state: WorkflowState) -> dict:
    """Run formal constraint satisfaction and convert to Deviation objects."""
    logger.info("=== Constraint Engine Node ===")

    reg_graph = state["registration_graph"]
    pub_graph = state["publication_graph"]

    engine = ConstraintEngine()
    results = engine.evaluate_all(reg_graph, pub_graph)

    violations = [r for r in results if r.status.value == "violated"]
    uncertain = [r for r in results if r.status.value == "uncertain"]
    satisfied = [r for r in results if r.status.value == "satisfied"]

    logger.info(
        f"Constraints: {len(satisfied)} satisfied, {len(violations)} violated, "
        f"{len(uncertain)} uncertain"
    )

    # Convert violations and uncertain results to deviations
    constraint_deviations = engine.violations_to_deviations(results)

    # Also score graph mutations
    scorer = SeverityScorer()
    mutation_deviations = []
    for mutation in state.get("graph_mutations", []):
        deviation = scorer.score_mutation(mutation)
        if deviation:
            mutation_deviations.append(deviation)

    all_deviations = constraint_deviations + mutation_deviations

    return {
        "constraint_results": results,
        "deviations": all_deviations,
    }


def critic_agent_node(state: WorkflowState) -> dict:
    """Self-reflect on deviations: filter false positives, handle uncertainty."""
    logger.info("=== Critic Agent Node ===")

    deviations = list(state.get("deviations", []))
    reviewed: list[Deviation] = []

    for dev in deviations:
        # Filter S0 trivial deviations when higher-severity issues exist
        if dev.severity == DeviationSeverity.S0_TRIVIAL:
            high_severity = any(
                d.severity.value >= "S3" for d in deviations if d.id != dev.id
            )
            if high_severity:
                logger.info(f"Filtering S0 deviation {dev.id}")
                continue

        # Deduplicate: if constraint_engine and graph_diff both flagged same thing
        is_duplicate = False
        for existing in reviewed:
            if (
                existing.category == dev.category
                and existing.source != dev.source
                and existing.severity == dev.severity
            ):
                # Keep the higher-confidence one
                if dev.confidence > existing.confidence:
                    reviewed.remove(existing)
                else:
                    is_duplicate = True
                break

        if not is_duplicate:
            # Boost confidence for multi-source detections
            related = [
                d for d in deviations
                if d.id != dev.id and d.category == dev.category
            ]
            if related:
                dev.confidence = min(1.0, dev.confidence + 0.1 * len(related))

            reviewed.append(dev)

    # Generate uncertainty summary
    uncertain_devs = [d for d in reviewed if d.uncertainty.is_uncertain]
    if uncertain_devs:
        logger.info(
            f"Critic: {len(uncertain_devs)} deviations flagged as uncertain — "
            f"human review recommended"
        )

    logger.info(f"Critic reviewed: {len(deviations)} → {len(reviewed)} deviations")

    return {"deviations": reviewed}


def report_generator_node(state: WorkflowState) -> dict:
    """Compile the final AuditLedger."""
    logger.info("=== Report Generator Node ===")

    generator = LedgerGenerator()
    ledger = generator.generate(
        registration_contract=state["registration_contract"],
        publication_contract=state["publication_contract"],
        deviations=state.get("deviations", []),
        constraint_violations=[
            r.violation_detail or r.description
            for r in state.get("constraint_results", [])
            if r.status.value == "violated"
        ],
        graph_mutations=state.get("graph_mutations", []),
    )

    logger.info(
        f"Generated audit ledger: {ledger.total_deviations} deviations, "
        f"severity: {ledger.severity_counts}, "
        f"uncertain: {ledger.uncertainty_summary or 'none'}"
    )

    return {"audit_ledger": ledger}


# --- Workflow Builder ---

class VerificationWorkflow:
    """Builds and runs the LangGraph verification workflow.

    Five-node pipeline:
    1. ContractExtractor — Compile documents into Scientific IR
    2. GraphDiffNode — Build graphs, compute structural + semantic diff
    3. ConstraintEngine — Formal constraint satisfaction (6 rules)
    4. CriticAgent — Self-reflect, deduplicate, handle uncertainty
    5. ReportGenerator — Compile final audit ledger
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(WorkflowState)

        workflow.add_node("contract_extractor", contract_extractor_node)
        workflow.add_node("graph_diff", graph_diff_node)
        workflow.add_node("constraint_engine", constraint_engine_node)
        workflow.add_node("critic", critic_agent_node)
        workflow.add_node("report_generator", report_generator_node)

        workflow.set_entry_point("contract_extractor")
        workflow.add_edge("contract_extractor", "graph_diff")
        workflow.add_edge("graph_diff", "constraint_engine")
        workflow.add_edge("constraint_engine", "critic")
        workflow.add_edge("critic", "report_generator")
        workflow.add_edge("report_generator", END)

        return workflow.compile()

    def run(
        self,
        registration_doc: Optional[ParsedDocument] = None,
        publication_doc: Optional[ParsedDocument] = None,
        use_mock: bool = False,
        model: Optional[str] = None,
    ) -> WorkflowState:
        """Run the full verification pipeline.

        Args:
            registration_doc: Parsed registration document
            publication_doc: Parsed publication document
            use_mock: Use synthetic contracts instead of LLM extraction
            model: Override LLM model for extraction (e.g., 'gpt-4o', 'claude-sonnet-4-20250514')
        """
        initial_state: WorkflowState = {
            "registration_doc": registration_doc,
            "publication_doc": publication_doc,
            "registration_contract": None,
            "publication_contract": None,
            "registration_graph": None,
            "publication_graph": None,
            "graph_mutations": [],
            "constraint_results": [],
            "deviations": [],
            "audit_ledger": None,
            "errors": [],
            "use_mock": use_mock,
            "model": model,
        }

        result = self.graph.invoke(initial_state)
        return result
