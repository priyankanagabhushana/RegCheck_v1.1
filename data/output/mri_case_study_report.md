# RegCheck v1.1 — Scientific Integrity Audit Report

**Generated:** 2026-07-03 13:52:27
**Registration:** OSF_2026_MRI_reg
**Publication:** OSF_2026_MRI_pub
**Total Deviations:** 19


## Severity Distribution

- 🟢 **S1** (S1_ADMINISTRATIVE): 6
- 🟡 **S2** (S2_REPORTING_GAP): 7
- 🟠 **S3** (S3_METHODOLOGICAL): 4
- 🔴 **S4** (S4_INFERENTIAL): 2

## Contract Comparison

| Field | Registration | Publication |
|-------|-------------|-------------|
| Title | Functional Connectivity Predicts Working Memory Performance: A Multi-Site fMRI Study | Functional Connectivity Predicts Working Memory Performance: A Multi-Site fMRI Study |
| Hypotheses | 2 | 1 |
| Outcomes | 2 | 2 |
| Analyses | 2 | 1 |
| Sample Size | N=120 | N=98 |

## Detected Deviations

### 1. [DeviationSeverity.S4_INFERENTIAL] S4_INFERENTIAL — constraint_c4

[C4] Hypothesis Presence: Missing in publication: Hypothesis 'Connectivity-behavior relationships will be consistent across Siemens and GE scanners' (H2)

- **Source:** constraint_engine
- **Confidence:** 90%

### 2. [DeviationSeverity.S4_INFERENTIAL] S4_INFERENTIAL — hypothesis_missing

Node 'H2' (hypothesis) present in registration but removed in publication

- **Source:** graph_diff
- **Confidence:** 80%

**Suggested Editorial Query:**
> The registered hypothesis 'N/A' does not appear to be addressed in the publication. Was this hypothesis dropped? If so, was this decision documented?

### 3. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — constraint_c6

[C6] Exclusion Criteria Consistency: 1 new exclusion criterion(a) added in publication

- **Source:** constraint_engine
- **Confidence:** 40%

### 4. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — constraint_mri-c2

[MRI-C2] Cross-Vendor Robustness: Cross-vendor robustness checks were dropped from publication

- **Source:** constraint_engine
- **Confidence:** 90%

### 5. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — analysis_removed

Node 'SA2' (analysis) present in registration but removed in publication

- **Source:** graph_diff
- **Confidence:** 80%

### 6. [DeviationSeverity.S3_METHODOLOGICAL] S3_METHODOLOGICAL — analysis_attribute_change

Attribute 'covariates' of node 'SA1' changed: '['site', 'head_motion_fd']' → '['site']'

- **Source:** graph_diff
- **Confidence:** 80%

### 7. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — constraint_c2

[C2] Sample Size Consistency: Planned N=120, Reported N=98. Drop of 18%.

- **Source:** constraint_engine
- **Confidence:** 90%

### 8. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — constraint_mri-c1

[MRI-C1] MRI Scanner Parameters: tr_ms changed: '2000.0' → '1500.0'

- **Source:** constraint_engine
- **Confidence:** 90%

### 9. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — claim_added

Node 'C1' (claim) added in publication (not in registration)

- **Source:** graph_diff
- **Confidence:** 80%

### 10. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — exclusion_criterion_added

Node 'E4' (exclusion_criterion) added in publication (not in registration)

- **Source:** graph_diff
- **Confidence:** 80%

### 11. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — exclusion_criterion_attribute_change

Attribute 'label' of node 'E1' changed: 'Head motion > 3mm translation or 3° rotation' → 'Head motion > 2mm translation or 2° rotation'

- **Source:** graph_diff
- **Confidence:** 80%

### 12. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — sample_size

Attribute 'actual_n' of node 'sample_size' changed: 'None' → '98'

- **Source:** graph_diff
- **Confidence:** 80%

### 13. [DeviationSeverity.S2_REPORTING_GAP] S2_REPORTING_GAP — structural_change

Edge C1 → H1 added in publication

- **Source:** graph_diff
- **Confidence:** 80%

### 14. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — mri_parameters_attribute_change

Attribute 'cross_vendor_checks' of node 'mri_params' changed: 'True' → 'False'

- **Source:** graph_diff
- **Confidence:** 80%

### 15. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — mri_parameters_attribute_change

Attribute 'preprocessing_pipeline' of node 'mri_params' changed: 'fMRIPrep 23.1.0 + ICA-AROMA denoising' → 'fMRIPrep 23.1.0'

- **Source:** graph_diff
- **Confidence:** 80%

### 16. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — mri_parameters_attribute_change

Attribute 'tr_ms' of node 'mri_params' changed: '2000.0' → '1500.0'

- **Source:** graph_diff
- **Confidence:** 80%

### 17. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — mri_parameters_attribute_change

Attribute 'uncertainty_quantification' of node 'mri_params' changed: 'Bootstrap confidence intervals (1000 resamples) + physics-informed signal-to-noise estimation' → 'p-values with FDR correction'

- **Source:** graph_diff
- **Confidence:** 80%

### 18. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — parameter_attribute_change

Attribute 'dropout_rate' of node 'sample_size' changed: '0.1' → '0.183'

- **Source:** graph_diff
- **Confidence:** 80%

### 19. [DeviationSeverity.S1_ADMINISTRATIVE] S1_ADMINISTRATIVE — analysis_attribute_change

Attribute 'independent_variables' of node 'SA1' changed: '['connectivity', 'scanner_vendor', 'age', 'sex']' → '['connectivity', 'age', 'sex']'

- **Source:** graph_diff
- **Confidence:** 80%


## Deterministic Constraint Violations

1. Planned N=120, Reported N=98. Drop of 18%.
2. Missing in publication: Hypothesis 'Connectivity-behavior relationships will be consistent across Siemens and GE scanners' (H2)
3. tr_ms changed: '2000.0' → '1500.0'
4. Cross-vendor robustness checks were dropped from publication

## Graph Diff Summary

```
Graph Diff Summary: 14 total mutations detected
  - node_removed: 2
  - node_added: 2
  - attribute_changed: 9
  - edge_added: 1

Detailed mutations:
  [node_removed] Node 'H2' (hypothesis) present in registration but removed in publication
  [node_removed] Node 'SA2' (analysis) present in registration but removed in publication
  [node_added] Node 'C1' (claim) added in publication (not in registration)
  [node_added] Node 'E4' (exclusion_criterion) added in publication (not in registration)
  [attribute_changed] Attribute 'label' of node 'E1' changed: 'Head motion > 3mm translation or 3° rotation' → 'Head motion > 2mm translation or 2° rotation'
  [attribute_changed] Attribute 'cross_vendor_checks' of node 'mri_params' changed: 'True' → 'False'
  [attribute_changed] Attribute 'preprocessing_pipeline' of node 'mri_params' changed: 'fMRIPrep 23.1.0 + ICA-AROMA denoising' → 'fMRIPrep 23.1.0'
  [attribute_changed] Attribute 'tr_ms' of node 'mri_params' changed: '2000.0' → '1500.0'
  [attribute_changed] Attribute 'uncertainty_quantification' of node 'mri_params' changed: 'Bootstrap confidence intervals (1000 resamples) + physics-informed signal-to-noise estimation' → 'p-values with FDR correction'
  [attribute_changed] Attribute 'dropout_rate' of node 'sample_size' changed: '0.1' → '0.183'
  [attribute_changed] Attribute 'actual_n' of node 'sample_size' changed: 'None' → '98'
  [attribute_changed] Attribute 'covariates' of node 'SA1' changed: '['site', 'head_motion_fd']' → '['site']'
  [attribute_changed] Attribute 'independent_variables' of node 'SA1' changed: '['connectivity', 'scanner_vendor', 'age', 'sex']' → '['connectivity', 'age', 'sex']'
  [edge_added] Edge C1 → H1 added in publication
```

## Suggested Editorial Queries

The following questions are suggested for the authors based on detected deviations of severity S3 or higher:

**1. [DeviationSeverity.S4_INFERENTIAL] hypothesis_missing:**
> The registered hypothesis 'N/A' does not appear to be addressed in the publication. Was this hypothesis dropped? If so, was this decision documented?
