# RegCheck v1.1 — Scientific Integrity Audit Report

**Generated:** 2026-07-03 13:44:04
**Registration:** NCT04123456_reg
**Publication:** NCT04123456_pub
**Total Deviations:** 25


## Severity Distribution

- 🟢 **S1** (S1_ADMINISTRATIVE): 5
- 🟡 **S2** (S2_REPORTING_GAP): 11
- 🟠 **S3** (S3_METHODOLOGICAL): 5
- 🔴 **S4** (S4_INFERENTIAL): 3
- 🔴 **S5** (S5_BIAS_CRITICAL): 1

## Contract Comparison

| Field | Registration | Publication |
|-------|-------------|-------------|
| Title | Efficacy of Cognitive Behavioral Therapy for Generalized Anxiety Disorder: A Randomized Controlled Trial | Efficacy of Cognitive Behavioral Therapy for Generalized Anxiety Disorder: A Randomized Controlled Trial |
| Hypotheses | 3 | 3 |
| Outcomes | 3 | 3 |
| Analyses | 2 | 1 |
| Sample Size | N=200 | N=147 |

## Detected Deviations

### 1. [DeviationSeverity.S5_BIAS_CRITICAL] S5_BIAS_CRITICAL — constraint_c1

[C1] Primary Outcome Equality: Primary outcome changed: 'GAD-7 Anxiety Scale' → 'State-Trait Anxiety Inventory (STAI)'

- **Source:** constraint_engine
- **Confidence:** 90%

### 2. [DeviationSeverity.S4_INFERENTIAL] S4_INFERENTIAL — constraint_c3

[C3] Analysis Model Compatibility: Analysis 'SA1': 'ANCOVA' → 'Independent samples t-test'

- **Source:** constraint_engine
- **Confidence:** 90%

### 3. [DeviationSeverity.S4_INFERENTIAL] S4_INFERENTIAL — constraint_c4

[C4] Hypothesis Presence: Missing in publication: Hypothesis 'CBT will improve sleep quality as measured by PSQI' (H3)

- **Source:** constraint_engine
- **Confidence:** 90%

### 4. [DeviationSeverity.S4_INFERENTIAL] S4_INFERENTIAL — hypothesis_missing

Node 'H3' (hypothesis) present in registration but removed in publication

- **Source:** graph_diff
- **Confidence:** 80%

**Suggested Editorial Query:**
> The registered hypothesis 'N/A' does not appear to be addressed in the publication. Was this hypothesis dropped? If so, was this decision documented?

### 5. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — constraint_c5

[C5] Claim-Hypothesis Mapping: Unmapped claims: Claim 'C1' maps to 'H4' which is not in registration

- **Source:** constraint_engine
- **Confidence:** 90%

### 6. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — exclusion_criterion_removed

Node 'E3' (exclusion_criterion) present in registration but removed in publication

- **Source:** graph_diff
- **Confidence:** 80%

### 7. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — analysis_removed

Node 'SA2' (analysis) present in registration but removed in publication

- **Source:** graph_diff
- **Confidence:** 80%

### 8. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — analysis_attribute_change

Attribute 'covariates' of node 'SA1' changed: '['GAD-7 baseline', 'age', 'gender', 'medication_status']' → '[]'

- **Source:** graph_diff
- **Confidence:** 80%

### 9. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — analysis_attribute_change

Attribute 'corrections' of node 'SA1' changed: '['Bonferroni']' → '[]'

- **Source:** graph_diff
- **Confidence:** 80%

### 10. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — constraint_c2

[C2] Sample Size Consistency: Planned N=200, Reported N=147. Drop of 26%.

- **Source:** constraint_engine
- **Confidence:** 90%

### 11. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — constraint_c6

[C6] Exclusion Criteria Consistency: 1 exclusion criterion(a) removed from registration

- **Source:** constraint_engine
- **Confidence:** 90%

### 12. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — hypothesis_added

Node 'H4' (hypothesis) added in publication (not in registration)

- **Source:** graph_diff
- **Confidence:** 80%

### 13. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — claim_added

Node 'C1' (claim) added in publication (not in registration)

- **Source:** graph_diff
- **Confidence:** 80%

### 14. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — hypothesis_attribute_change

Attribute 'variables' of node 'H1' changed: '['anxiety_symptoms', 'CBT', 'waitlist_control']' → '['anxiety_symptoms', 'CBT']'

- **Source:** graph_diff
- **Confidence:** 80%

### 15. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — hypothesis_change

Attribute 'label' of node 'H1' changed: 'CBT will reduce anxiety symptoms by at least 30% compared to waitlist control at 12 weeks' → 'CBT will reduce anxiety symptoms compared to waitlist control at 12 weeks'

- **Source:** graph_diff
- **Confidence:** 80%

### 16. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — hypothesis_attribute_change

Attribute 'variables' of node 'H2' changed: '['anxiety_symptoms', 'follow_up']' → '[]'

- **Source:** graph_diff
- **Confidence:** 80%

### 17. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — sample_size

Attribute 'actual_n' of node 'sample_size' changed: 'None' → '147'

- **Source:** graph_diff
- **Confidence:** 80%

### 18. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — analysis_attribute_change

Attribute 'label' of node 'SA1' changed: 'ANCOVA' → 'Independent samples t-test'

- **Source:** graph_diff
- **Confidence:** 80%

### 19. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — outcome_switch

Attribute 'label' of node 'O1' changed: 'GAD-7 Anxiety Scale' → 'State-Trait Anxiety Inventory (STAI)'

- **Source:** graph_diff
- **Confidence:** 80%

### 20. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — structural_change

Edge C1 → H4 added in publication

- **Source:** graph_diff
- **Confidence:** 80%

### 21. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — outcome_attribute_change

Attribute 'description' of node 'O2' changed: '9-item self-report measure of depression severity' → 'None'

- **Source:** graph_diff
- **Confidence:** 80%

### 22. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — parameter_attribute_change

Attribute 'dropout_rate' of node 'sample_size' changed: '0.15' → '0.265'

- **Source:** graph_diff
- **Confidence:** 80%

### 23. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — analysis_attribute_change

Attribute 'dependent_variable' of node 'SA1' changed: 'GAD-7 post-treatment' → 'STAI change score'

- **Source:** graph_diff
- **Confidence:** 80%

### 24. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — analysis_attribute_change

Attribute 'software' of node 'SA1' changed: 'R 4.3.0' → 'SPSS 28'

- **Source:** graph_diff
- **Confidence:** 80%

### 25. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — outcome_attribute_change

Attribute 'description' of node 'O1' changed: '7-item self-report measure of generalized anxiety' → '20-item self-report measure of state and trait anxiety'

- **Source:** graph_diff
- **Confidence:** 80%


## Deterministic Constraint Violations

1. Primary outcome changed: 'GAD-7 Anxiety Scale' → 'State-Trait Anxiety Inventory (STAI)'
2. Planned N=200, Reported N=147. Drop of 26%.
3. Analysis 'SA1': 'ANCOVA' → 'Independent samples t-test'
4. Missing in publication: Hypothesis 'CBT will improve sleep quality as measured by PSQI' (H3)
5. Unmapped claims: Claim 'C1' maps to 'H4' which is not in registration
6. 1 exclusion criterion(a) removed from registration

## Graph Diff Summary

```
Graph Diff Summary: 19 total mutations detected
  - node_removed: 3
  - node_added: 2
  - attribute_changed: 13
  - edge_added: 1

Detailed mutations:
  [node_removed] Node 'E3' (exclusion_criterion) present in registration but removed in publication
  [node_removed] Node 'SA2' (analysis) present in registration but removed in publication
  [node_removed] Node 'H3' (hypothesis) present in registration but removed in publication
  [node_added] Node 'H4' (hypothesis) added in publication (not in registration)
  [node_added] Node 'C1' (claim) added in publication (not in registration)
  [attribute_changed] Attribute 'description' of node 'O2' changed: '9-item self-report measure of depression severity' → 'None'
  [attribute_changed] Attribute 'variables' of node 'H1' changed: '['anxiety_symptoms', 'CBT', 'waitlist_control']' → '['anxiety_symptoms', 'CBT']'
  [attribute_changed] Attribute 'label' of node 'H1' changed: 'CBT will reduce anxiety symptoms by at least 30% compared to waitlist control at 12 weeks' → 'CBT will reduce anxiety symptoms compared to waitlist control at 12 weeks'
  [attribute_changed] Attribute 'variables' of node 'H2' changed: '['anxiety_symptoms', 'follow_up']' → '[]'
  [attribute_changed] Attribute 'actual_n' of node 'sample_size' changed: 'None' → '147'
  [attribute_changed] Attribute 'dropout_rate' of node 'sample_size' changed: '0.15' → '0.265'
  [attribute_changed] Attribute 'dependent_variable' of node 'SA1' changed: 'GAD-7 post-treatment' → 'STAI change score'
  [attribute_changed] Attribute 'software' of node 'SA1' changed: 'R 4.3.0' → 'SPSS 28'
  [attribute_changed] Attribute 'covariates' of node 'SA1' changed: '['GAD-7 baseline', 'age', 'gender', 'medication_status']' → '[]'
  [attribute_changed] Attribute 'corrections' of node 'SA1' changed: '['Bonferroni']' → '[]'
  [attribute_changed] Attribute 'label' of node 'SA1' changed: 'ANCOVA' → 'Independent samples t-test'
  [attribute_changed] Attribute 'description' of node 'O1' changed: '7-item self-report measure of generalized anxiety' → '20-item self-report measure of state and trait anxiety'
  [attribute_changed] Attribute 'label' of node 'O1' changed: 'GAD-7 Anxiety Scale' → 'State-Trait Anxiety Inventory (STAI)'
  [edge_added] Edge C1 → H4 added in publication
```

## Suggested Editorial Queries

The following questions are suggested for the authors based on detected deviations of severity S3 or higher:

**1. [DeviationSeverity.S4_INFERENTIAL] hypothesis_missing:**
> The registered hypothesis 'N/A' does not appear to be addressed in the publication. Was this hypothesis dropped? If so, was this decision documented?
