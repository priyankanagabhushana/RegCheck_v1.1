# RegCheck v1.1 — Scientific Integrity Audit Report

**Generated:** 2026-07-03 13:42:36
**Registration:** mock_registration
**Publication:** mock_publication
**Total Deviations:** 6


## Severity Distribution

- 🟡 **S2** (S2_REPORTING_GAP): 4
- 🔴 **S4** (S4_INFERENTIAL): 1
- 🔴 **S5** (S5_BIAS_CRITICAL): 1

## Contract Comparison

| Field | Registration | Publication |
|-------|-------------|-------------|
| Title | Mock Registration Document | Mock Publication Document |
| Hypotheses | 2 | 2 |
| Outcomes | 2 | 2 |
| Analyses | 1 | 1 |
| Sample Size | N=200 | N=150 |

## Detected Deviations

### 1. [DeviationSeverity.S5_BIAS_CRITICAL] S5_BIAS_CRITICAL — constraint_c1

[C1] Primary Outcome Equality: Primary outcome changed: 'GAD-7 Anxiety Scale' → 'STAI Anxiety Scale'

- **Source:** constraint_engine
- **Confidence:** 90%

### 2. [DeviationSeverity.S4_INFERENTIAL] S4_INFERENTIAL — constraint_c3

[C3] Analysis Model Compatibility: Analysis 'SA1': 'ANCOVA' → 't-test'

- **Source:** constraint_engine
- **Confidence:** 90%

### 3. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — constraint_c2

[C2] Sample Size Consistency: Planned N=200, Reported N=150. Drop of 25%.

- **Source:** constraint_engine
- **Confidence:** 90%

### 4. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — outcome_switch

Attribute 'label' of node 'O1' changed: 'GAD-7 Anxiety Scale' → 'STAI Anxiety Scale'

- **Source:** graph_diff
- **Confidence:** 80%

### 5. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — sample_size

Attribute 'actual_n' of node 'sample_size' changed: 'None' → '150'

- **Source:** graph_diff
- **Confidence:** 80%

### 6. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — analysis_attribute_change

Attribute 'label' of node 'SA1' changed: 'ANCOVA' → 't-test'

- **Source:** graph_diff
- **Confidence:** 80%


## Deterministic Constraint Violations

1. Primary outcome changed: 'GAD-7 Anxiety Scale' → 'STAI Anxiety Scale'
2. Planned N=200, Reported N=150. Drop of 25%.
3. Analysis 'SA1': 'ANCOVA' → 't-test'

## Graph Diff Summary

```
Graph Diff Summary: 3 total mutations detected
  - attribute_changed: 3

Detailed mutations:
  [attribute_changed] Attribute 'label' of node 'O1' changed: 'GAD-7 Anxiety Scale' → 'STAI Anxiety Scale'
  [attribute_changed] Attribute 'actual_n' of node 'sample_size' changed: 'None' → '150'
  [attribute_changed] Attribute 'label' of node 'SA1' changed: 'ANCOVA' → 't-test'
```