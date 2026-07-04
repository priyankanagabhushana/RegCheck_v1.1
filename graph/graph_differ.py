"""Graph Differ - Compares Registration Graph vs Publication Graph.

Detects both structural mutations AND semantic relationship changes.
Structural: added/removed nodes, changed attributes, changed edges.
Semantic: inferential drift (e.g., Outcome tested_by Mixed Model → tested_by t-test).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

import networkx as nx
from pydantic import BaseModel, Field


class MutationType(str, Enum):
    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    ATTRIBUTE_CHANGED = "attribute_changed"
    EDGE_ADDED = "edge_added"
    EDGE_REMOVED = "edge_removed"
    RELATIONSHIP_DRIFT = "relationship_drift"  # Semantic: same edge type, different target


class SemanticDriftType(str, Enum):
    """Types of semantic drift in relationships."""
    INFERENTIAL_DRIFT = "inferential_drift"      # Analysis method changed
    OUTCOME_DRIFT = "outcome_drift"              # Outcome measure changed
    HYPOTHESIS_DRIFT = "hypothesis_drift"        # Hypothesis scope changed
    EVIDENCE_GAP = "evidence_gap"               # Claim lacks supporting evidence
    METHODOLOGICAL_DRIFT = "methodological_drift"  # Method changed for same goal


class GraphMutation(BaseModel):
    """A detected structural or semantic change between two protocol graphs."""
    mutation_type: MutationType
    node_id: Optional[str] = None
    edge: Optional[tuple[str, str]] = None
    node_type: Optional[str] = None
    attribute_name: Optional[str] = None
    registration_value: Optional[Any] = None
    publication_value: Optional[Any] = None
    description: str = ""
    semantic_drift: Optional[SemanticDriftType] = None
    is_semantic: bool = False


class GraphDiffer:
    """Compares two protocol graphs and returns structured mutations.

    Two levels of comparison:
    1. Structural diff: node/edge/attribute changes
    2. Semantic diff: relationship drift detection (inferential, outcome, methodological)
    """

    def diff(
        self,
        reg_graph: nx.DiGraph,
        pub_graph: nx.DiGraph,
    ) -> list[GraphMutation]:
        """Compare registration graph against publication graph.

        Returns both structural and semantic mutations.
        """
        mutations: list[GraphMutation] = []

        mutations.extend(self._find_node_changes(reg_graph, pub_graph))
        mutations.extend(self._find_attribute_changes(reg_graph, pub_graph))
        mutations.extend(self._find_edge_changes(reg_graph, pub_graph))
        mutations.extend(self._find_semantic_drift(reg_graph, pub_graph))

        return mutations

    def check_constraints(
        self,
        reg_graph: nx.DiGraph,
        pub_graph: nx.DiGraph,
    ) -> list[str]:
        """Run deterministic constraint checks (neuro-symbolic rules).

        Deprecated: use ConstraintEngine for formal constraint satisfaction.
        Kept for backward compatibility.
        """
        violations: list[str] = []

        violations.extend(self._check_sample_size(reg_graph, pub_graph))
        violations.extend(self._check_primary_outcomes(reg_graph, pub_graph))
        violations.extend(self._check_analysis_models(reg_graph, pub_graph))
        violations.extend(self._check_hypothesis_presence(reg_graph, pub_graph))

        return violations

    def _find_semantic_drift(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[GraphMutation]:
        """Detect semantic relationship drift — the key innovation over structural diff.

        Examples:
        - Outcome O1 tested_by ANCOVA → tested_by t-test (inferential drift)
        - Hypothesis H1 scope narrowed/expanded (hypothesis drift)
        - Claim C1 has no supporting evidence in pub (evidence gap)
        """
        mutations = []
        common_nodes = set(reg_graph.nodes) & set(pub_graph.nodes)

        for node_id in common_nodes:
            rdata = reg_graph.nodes[node_id]
            pdata = pub_graph.nodes[node_id]
            node_type = rdata.get("node_type")

            # Inferential drift: analysis relationship changed
            if node_type == "outcome":
                mutations.extend(
                    self._check_outcome_drift(node_id, rdata, pdata, reg_graph, pub_graph)
                )

            # Evidence gap: claim with no supporting evidence
            if node_type == "claim":
                mutations.extend(
                    self._check_evidence_gap(node_id, rdata, pdata, reg_graph, pub_graph)
                )

        return mutations

    def _check_outcome_drift(
        self, node_id: str, rdata: dict, pdata: dict,
        reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[GraphMutation]:
        """Check if an outcome's testing relationship changed (inferential drift)."""
        mutations = []

        # Get what tests this outcome in both graphs
        reg_testers = self._get_incoming_by_type(reg_graph, node_id, "measured_at")
        pub_testers = self._get_incoming_by_type(pub_graph, node_id, "measured_at")

        reg_models = {reg_graph.nodes[t].get("label", t) for t in reg_testers}
        pub_models = {pub_graph.nodes[t].get("label", t) for t in pub_testers}

        if reg_models and pub_models and reg_models != pub_models:
            mutations.append(GraphMutation(
                mutation_type=MutationType.RELATIONSHIP_DRIFT,
                node_id=node_id,
                node_type="outcome",
                registration_value=list(reg_models),
                publication_value=list(pub_models),
                description=(
                    f"Inferential drift on '{node_id}': "
                    f"tested by {reg_models} in registration "
                    f"→ tested by {pub_models} in publication"
                ),
                semantic_drift=SemanticDriftType.INFERENTIAL_DRIFT,
                is_semantic=True,
            ))

        return mutations

    def _check_evidence_gap(
        self, node_id: str, rdata: dict, pdata: dict,
        reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[GraphMutation]:
        """Check if a claim has supporting evidence in the publication graph."""
        mutations = []

        pub_supporters = self._get_incoming_by_type(pub_graph, node_id, "supported_by")
        if not pub_supporters:
            mutations.append(GraphMutation(
                mutation_type=MutationType.RELATIONSHIP_DRIFT,
                node_id=node_id,
                node_type="claim",
                description=(
                    f"Evidence gap: Claim '{pdata.get('label', node_id)[:60]}' "
                    f"has no supporting evidence edges in publication graph"
                ),
                semantic_drift=SemanticDriftType.EVIDENCE_GAP,
                is_semantic=True,
            ))

        return mutations

    @staticmethod
    def _get_incoming_by_type(
        G: nx.DiGraph, node_id: str, edge_type: str
    ) -> list[str]:
        """Get source nodes of incoming edges of a specific type."""
        return [
            src for src, _, edata in G.in_edges(node_id, data=True)
            if edata.get("edge_type") == edge_type
        ]

    def _find_node_changes(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[GraphMutation]:
        mutations = []
        reg_nodes = set(reg_graph.nodes)
        pub_nodes = set(pub_graph.nodes)

        # Nodes removed (in registration but not publication)
        for node_id in reg_nodes - pub_nodes:
            data = reg_graph.nodes[node_id]
            mutations.append(GraphMutation(
                mutation_type=MutationType.NODE_REMOVED,
                node_id=node_id,
                node_type=data.get("node_type"),
                description=f"Node '{node_id}' ({data.get('node_type')}) present in registration but removed in publication",
            ))

        # Nodes added (in publication but not registration)
        for node_id in pub_nodes - reg_nodes:
            data = pub_graph.nodes[node_id]
            mutations.append(GraphMutation(
                mutation_type=MutationType.NODE_ADDED,
                node_id=node_id,
                node_type=data.get("node_type"),
                description=f"Node '{node_id}' ({data.get('node_type')}) added in publication (not in registration)",
            ))

        return mutations

    def _find_attribute_changes(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[GraphMutation]:
        mutations = []
        common_nodes = set(reg_graph.nodes) & set(pub_graph.nodes)

        # Attributes to skip (metadata)
        skip_attrs = {"doc_id"}

        for node_id in common_nodes:
            reg_data = reg_graph.nodes[node_id]
            pub_data = pub_graph.nodes[node_id]

            all_keys = set(reg_data.keys()) | set(pub_data.keys())
            for key in all_keys:
                if key in skip_attrs:
                    continue
                reg_val = reg_data.get(key)
                pub_val = pub_data.get(key)

                if reg_val != pub_val:
                    mutations.append(GraphMutation(
                        mutation_type=MutationType.ATTRIBUTE_CHANGED,
                        node_id=node_id,
                        node_type=reg_data.get("node_type"),
                        attribute_name=key,
                        registration_value=reg_val,
                        publication_value=pub_val,
                        description=(
                            f"Attribute '{key}' of node '{node_id}' changed: "
                            f"'{reg_val}' → '{pub_val}'"
                        ),
                    ))

        return mutations

    def _find_edge_changes(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[GraphMutation]:
        mutations = []
        reg_edges = set(reg_graph.edges)
        pub_edges = set(pub_graph.edges)

        for edge in reg_edges - pub_edges:
            mutations.append(GraphMutation(
                mutation_type=MutationType.EDGE_REMOVED,
                edge=edge,
                description=f"Edge {edge[0]} → {edge[1]} removed in publication",
            ))

        for edge in pub_edges - reg_edges:
            mutations.append(GraphMutation(
                mutation_type=MutationType.EDGE_ADDED,
                edge=edge,
                description=f"Edge {edge[0]} → {edge[1]} added in publication",
            ))

        return mutations

    def _check_sample_size(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[str]:
        violations = []

        reg_ss = reg_graph.nodes.get("sample_size")
        pub_ss = pub_graph.nodes.get("sample_size")

        if reg_ss and pub_ss:
            planned = reg_ss.get("planned_n")
            actual = pub_ss.get("actual_n") or pub_ss.get("planned_n")

            if planned and actual and actual < planned * 0.5:
                violations.append(
                    f"SAMPLE_SIZE_VIOLATION: Planned N={planned} but reported N={actual}. "
                    f"Drop exceeds 50% without documented justification."
                )

        return violations

    def _check_primary_outcomes(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[str]:
        violations = []

        reg_primaries = {
            n for n, d in reg_graph.nodes(data=True)
            if d.get("node_type") == "outcome" and d.get("outcome_type") == "primary"
        }
        pub_primaries = {
            n for n, d in pub_graph.nodes(data=True)
            if d.get("node_type") == "outcome" and d.get("outcome_type") == "primary"
        }

        for outcome_id in reg_primaries:
            if outcome_id not in pub_primaries:
                reg_label = reg_graph.nodes[outcome_id].get("label", outcome_id)
                violations.append(
                    f"OUTCOME_SWITCH: Primary outcome '{reg_label}' ({outcome_id}) "
                    f"in registration is not listed as primary in publication."
                )
            elif outcome_id in pub_graph.nodes:
                reg_label = reg_graph.nodes[outcome_id].get("label", "")
                pub_label = pub_graph.nodes[outcome_id].get("label", "")
                if reg_label and pub_label and reg_label.lower() != pub_label.lower():
                    violations.append(
                        f"OUTCOME_SWITCH: Primary outcome '{reg_label}' ({outcome_id}) "
                        f"changed to '{pub_label}' in publication."
                    )

        return violations

    def _check_analysis_models(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[str]:
        violations = []
        common_nodes = set(reg_graph.nodes) & set(pub_graph.nodes)

        for node_id in common_nodes:
            reg_data = reg_graph.nodes[node_id]
            pub_data = pub_graph.nodes[node_id]

            if reg_data.get("node_type") == "analysis":
                reg_model = reg_data.get("label", "")
                pub_model = pub_data.get("label", "")

                if reg_model and pub_model and reg_model.lower() != pub_model.lower():
                    violations.append(
                        f"ANALYSIS_CHANGE: Analysis '{node_id}' model changed from "
                        f"'{reg_model}' to '{pub_model}'."
                    )

        return violations

    def _check_hypothesis_presence(
        self, reg_graph: nx.DiGraph, pub_graph: nx.DiGraph
    ) -> list[str]:
        violations = []

        reg_hypotheses = {
            n for n, d in reg_graph.nodes(data=True)
            if d.get("node_type") == "hypothesis"
        }

        for h_id in reg_hypotheses:
            if h_id not in pub_graph.nodes:
                reg_label = reg_graph.nodes[h_id].get("label", h_id)
                violations.append(
                    f"HYPOTHESIS_MISSING: Hypothesis '{reg_label}' ({h_id}) "
                    f"from registration is not present in publication."
                )

        return violations

    @staticmethod
    def summarize_mutations(mutations: list[GraphMutation]) -> str:
        """Generate a human-readable summary of mutations."""
        if not mutations:
            return "No structural differences detected between registration and publication graphs."

        type_counts: dict[str, int] = {}
        for m in mutations:
            type_counts[m.mutation_type.value] = type_counts.get(m.mutation_type.value, 0) + 1

        lines = [f"Graph Diff Summary: {len(mutations)} total mutations detected"]
        for mtype, count in type_counts.items():
            lines.append(f"  - {mtype}: {count}")

        lines.append("\nDetailed mutations:")
        for m in mutations:
            lines.append(f"  [{m.mutation_type.value}] {m.description}")

        return "\n".join(lines)
