"""Evaluation Framework — per-constraint metrics, ablation, confusion matrix.

Exports:
    evaluate_dataset() — run full evaluation against ground truth
    ConstraintMetrics — per-constraint precision/recall/F1
    AblationTable — per-configuration ablation results
    ConfusionMatrix — detection category confusion matrix
    GroundTruth, GroundTruthDataset — ground-truth data structures
"""

from .evaluator import EvalReport, PipelineEvaluator, evaluate_dataset
from .groundtruth import (
    GroundTruth,
    GroundTruthDataset,
    load_compare_dataset,
    load_known_deviations,
)
from .metrics import (
    AblationTable,
    ConfusionMatrix,
    ConstraintMetrics,
    compute_ablation_table,
    compute_constraint_metrics,
)

__all__ = [
    "AblationTable",
    "ConfusionMatrix",
    "ConstraintMetrics",
    "EvalReport",
    "GroundTruth",
    "GroundTruthDataset",
    "PipelineEvaluator",
    "compute_ablation_table",
    "compute_constraint_metrics",
    "evaluate_dataset",
    "load_compare_dataset",
    "load_known_deviations",
]
