"""Protocol Graph Builder - Converts ScientificContract into NetworkX graph.

Node types: Hypothesis, Outcome, Parameter, Analysis, Claim, Evidence
Edge types: tested_by, constrained_by, measured_at, supported_by, maps_to
"""

from __future__ import annotations

from typing import Optional

import networkx as nx

from schemas.ir import ScientificContract


class ProtocolGraphBuilder:
    """Builds a NetworkX graph from a ScientificContract.

    Each scientific object becomes a node with typed attributes.
    Edges represent relationships between objects.
    """

    def build(self, contract: ScientificContract) -> nx.DiGraph:
        """Convert a ScientificContract into a directed graph.

        Args:
            contract: The compiled ScientificContract

        Returns:
            NetworkX DiGraph with typed nodes and edges
        """
        G = nx.DiGraph()
        G.graph["doc_id"] = contract.doc_id
        G.graph["doc_type"] = contract.doc_type

        self._add_hypothesis_nodes(G, contract)
        self._add_outcome_nodes(G, contract)
        self._add_analysis_nodes(G, contract)
        self._add_claim_nodes(G, contract)
        self._add_sample_size_node(G, contract)
        self._add_exclusion_nodes(G, contract)
        self._add_domain_params_node(G, contract)

        return G

    def _add_hypothesis_nodes(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        for h in contract.hypotheses:
            G.add_node(
                h.id,
                node_type="hypothesis",
                label=h.description,
                hypothesis_type=h.hypothesis_type.value,
                variables=h.variables,
                direction=h.direction,
                status=h.status.value if hasattr(h, 'status') else "present",
                doc_id=contract.doc_id,
            )

    def _add_outcome_nodes(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        for o in contract.outcomes:
            G.add_node(
                o.id,
                node_type="outcome",
                label=o.measure,
                outcome_type=o.outcome_type.value,
                timepoint=o.timepoint,
                description=o.description,
                status=o.status.value if hasattr(o, 'status') else "present",
                doc_id=contract.doc_id,
            )

    def _add_analysis_nodes(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        for a in contract.analyses:
            G.add_node(
                a.id,
                node_type="analysis",
                label=a.model,
                dependent_variable=a.dependent_variable,
                independent_variables=a.independent_variables,
                covariates=a.covariates,
                corrections=a.corrections,
                software=a.software,
                doc_id=contract.doc_id,
            )
            # Edge: analysis tests hypothesis (if DV matches outcome)
            for o in contract.outcomes:
                if a.dependent_variable and o.measure and (
                    o.measure.lower() in a.dependent_variable.lower()
                    or a.dependent_variable.lower() in o.measure.lower()
                ):
                    G.add_edge(a.id, o.id, edge_type="measured_at")

    def _add_claim_nodes(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        for c in contract.claims:
            G.add_node(
                c.id,
                node_type="claim",
                label=c.text[:200],
                strength=c.strength,
                doc_id=contract.doc_id,
            )
            if c.mapped_hypothesis_id:
                G.add_edge(c.id, c.mapped_hypothesis_id, edge_type="maps_to")

    def _add_sample_size_node(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        if contract.sample_size:
            ss = contract.sample_size
            G.add_node(
                "sample_size",
                node_type="parameter",
                label=f"N={ss.planned_n or ss.actual_n}",
                planned_n=ss.planned_n,
                actual_n=ss.actual_n,
                dropout_rate=ss.dropout_rate,
                status=ss.status.value if hasattr(ss, 'status') else "present",
                doc_id=contract.doc_id,
            )

    def _add_exclusion_nodes(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        for ec in contract.exclusion_criteria:
            G.add_node(
                ec.id,
                node_type="exclusion_criterion",
                label=ec.description,
                criterion_type=ec.criterion_type,
                doc_id=contract.doc_id,
            )

    def _add_domain_params_node(self, G: nx.DiGraph, contract: ScientificContract) -> None:
        dp = contract.domain_params
        if dp and dp.mri:
            mri = dp.mri
            G.add_node(
                "mri_params",
                node_type="mri_parameters",
                label=f"MRI: {mri.scanner_field_strength or '?'}T",
                scanner_field_strength=mri.scanner_field_strength,
                tr_ms=mri.tr_ms,
                te_ms=mri.te_ms,
                voxel_size_mm=mri.voxel_size_mm,
                sequence_type=mri.sequence_type,
                region_of_interest=mri.region_of_interest,
                preprocessing_pipeline=mri.preprocessing_pipeline,
                cross_vendor_checks=mri.cross_vendor_checks,
                uncertainty_quantification=mri.uncertainty_quantification,
                doc_id=contract.doc_id,
            )

    @staticmethod
    def get_graph_summary(G: nx.DiGraph) -> dict:
        """Get a summary of graph contents."""
        type_counts: dict[str, int] = {}
        for _, data in G.nodes(data=True):
            nt = data.get("node_type", "unknown")
            type_counts[nt] = type_counts.get(nt, 0) + 1

        edge_counts: dict[str, int] = {}
        for _, _, data in G.edges(data=True):
            et = data.get("edge_type", "unknown")
            edge_counts[et] = edge_counts.get(et, 0) + 1

        return {
            "doc_id": G.graph.get("doc_id"),
            "doc_type": G.graph.get("doc_type"),
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "node_types": type_counts,
            "edge_types": edge_counts,
        }
