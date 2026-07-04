"""Per-constraint evaluation metrics with precision, recall, F1, confusion matrix.

Produces the exact format that PhD admissions committees expect:
    | Configuration       | Precision | Recall | F1   |
    | Full System         | 0.95      | 0.94   | 0.95 |
    | Without Graph       | 0.84      | 0.73   | 0.78 |
    | Without Constraints | 0.71      | 0.58   | 0.63 |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ConstraintMetrics:
    """Precision, recall, F1 for a single constraint or configuration."""
    constraint_id: str
    constraint_name: str = ""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0

    @property
    def accuracy(self) -> float:
        total = self.true_positives + self.false_positives + self.false_negatives + self.true_negatives
        return (self.true_positives + self.true_negatives) / total if total > 0 else 0.0

    def to_row(self) -> list[str]:
        return [
            self.constraint_id,
            f"{self.precision:.2f}",
            f"{self.recall:.2f}",
            f"{self.f1:.2f}",
            str(self.true_positives),
            str(self.false_positives),
            str(self.false_negatives),
        ]


@dataclass
class ConfusionMatrix:
    """NxN confusion matrix for multi-class evaluation."""
    labels: list[str] = field(default_factory=list)
    matrix: list[list[int]] = field(default_factory=list)

    def add_row(self, label: str, row: list[int]) -> None:
        self.labels.append(label)
        self.matrix.append(row)

    def to_text_table(self) -> str:
        if not self.labels:
            return "No data"
        header = " " * 20 + " ".join(f"{l:>6}" for l in self.labels)
        rows = [header]
        for i, label in enumerate(self.labels):
            row_str = f"{label:>20}" + " ".join(f"{v:>6}" for v in self.matrix[i])
            rows.append(row_str)
        return "\n".join(rows)


@dataclass
class AblationTable:
    """Per-configuration ablation results — the table professors love."""
    configurations: list[ConstraintMetrics] = field(default_factory=list)

    def add_configuration(self, cfg: ConstraintMetrics) -> None:
        self.configurations.append(cfg)

    def to_markdown(self) -> str:
        if not self.configurations:
            return "_No ablation data_"
        lines = [
            "| Configuration | Precision | Recall | F1 | TP | FP | FN |",
            "|--------------|-----------|--------|-----|----|----|----|",
        ]
        for cfg in self.configurations:
            row = " | ".join(cfg.to_row())
            lines.append(f"| {cfg.constraint_id} | {row} |")
        return "\n".join(lines)

    def to_rich_table(self):
        try:
            from rich.table import Table
            table = Table(title="Ablation Results")
            table.add_column("Configuration", style="cyan")
            table.add_column("Precision", justify="right")
            table.add_column("Recall", justify="right")
            table.add_column("F1", justify="right")
            table.add_column("TP", justify="right")
            table.add_column("FP", justify="right")
            table.add_column("FN", justify="right")
            for cfg in self.configurations:
                table.add_row(*cfg.to_row())
            return table
        except ImportError:
            return None


def compute_constraint_metrics(
    constraint_id: str,
    constraint_name: str,
    gt_pairs: list[dict],  # Each: {"has_deviation": bool, "detected": bool}
) -> ConstraintMetrics:
    """Compute precision/recall/F1 for a single constraint.

    Args:
        constraint_id: e.g., "C1", "C2"
        constraint_name: Human-readable name
        gt_pairs: List of ground-truth/detection pairs. Each dict has:
            - has_deviation: bool (ground truth — does this deviation exist?)
            - detected: bool (system output — was it detected?)
    """
    metrics = ConstraintMetrics(
        constraint_id=constraint_id,
        constraint_name=constraint_name,
    )
    for pair in gt_pairs:
        has = pair["has_deviation"]
        det = pair["detected"]
        if has and det:
            metrics.true_positives += 1
        elif not has and det:
            metrics.false_positives += 1
        elif has and not det:
            metrics.false_negatives += 1
        else:
            metrics.true_negatives += 1
    return metrics


def compute_ablation_table(
    full_metrics: ConstraintMetrics,
    no_graph_metrics: ConstraintMetrics,
    no_constraints_metrics: ConstraintMetrics,
    no_semantic_metrics: Optional[ConstraintMetrics] = None,
) -> AblationTable:
    """Build the ablation table that professors love."""
    table = AblationTable()
    table.add_configuration(ConstraintMetrics(
        constraint_id="Full System",
        constraint_name="All components",
        true_positives=full_metrics.true_positives,
        false_positives=full_metrics.false_positives,
        false_negatives=full_metrics.false_negatives,
        true_negatives=full_metrics.true_negatives,
    ))
    table.add_configuration(ConstraintMetrics(
        constraint_id="− Graph Diff",
        constraint_name="Graph diff disabled",
        true_positives=no_graph_metrics.true_positives,
        false_positives=no_graph_metrics.false_positives,
        false_negatives=no_graph_metrics.false_negatives,
        true_negatives=no_graph_metrics.true_negatives,
    ))
    table.add_configuration(ConstraintMetrics(
        constraint_id="− Constraints",
        constraint_name="Constraint engine disabled",
        true_positives=no_constraints_metrics.true_positives,
        false_positives=no_constraints_metrics.false_positives,
        false_negatives=no_constraints_metrics.false_negatives,
        true_negatives=no_constraints_metrics.true_negatives,
    ))
    if no_semantic_metrics:
        table.add_configuration(ConstraintMetrics(
            constraint_id="− Semantic Drift",
            constraint_name="Semantic drift disabled",
            true_positives=no_semantic_metrics.true_positives,
            false_positives=no_semantic_metrics.false_positives,
            false_negatives=no_semantic_metrics.false_negatives,
            true_negatives=no_semantic_metrics.true_negatives,
        ))
    return table
