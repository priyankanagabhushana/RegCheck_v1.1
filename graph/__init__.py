"""Protocol Graph Engine - NetworkX-based graph representation and differencing.

Converts ScientificContract IR into a knowledge graph and detects structural + semantic mutations.
"""

from .graph_builder import ProtocolGraphBuilder
from .graph_differ import GraphDiffer, GraphMutation, MutationType, SemanticDriftType

__all__ = [
    "ProtocolGraphBuilder", "GraphDiffer", "GraphMutation",
    "MutationType", "SemanticDriftType",
]
