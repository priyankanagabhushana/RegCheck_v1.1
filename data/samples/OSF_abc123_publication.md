# Publication: Functional Connectivity Predicts Working Memory Performance — A Multi-Site fMRI Study

## Authors
Zhang L, Patel R, Kim S, Liu W

## Abstract
This multi-site fMRI study examined whether functional connectivity between prefrontal and parietal regions predicts working memory performance.

### Methods

**Participants:** A total of 120 participants were recruited from two sites. After quality control, 98 participants were included in the final analysis.

**MRI Acquisition:**
- Scanner: 3.0 Tesla
- Repetition time (TR): 1500ms
- Echo time (TE): 30ms
- Sequence: Gradient-echo EPI (fMRI BOLD)
- Region of interest: DLPFC and PPC (bilateral)

**Preprocessing:** fMRIPrep 23.1.0. No additional denoising was applied.

**Primary Outcome:** DLPFC-PPC functional connectivity (Fisher z-transformed) correlated with N-back accuracy.

**Analysis:** Mixed-effects regression with working memory accuracy as dependent variable, connectivity + age + sex as independent variables, site as covariate. Software: FSL 6.0 + Python Nilearn. No permutation testing was performed; standard p-values with FDR correction were used.

### Results
Functional connectivity between DLPFC and PPC significantly predicted working memory accuracy (β=0.34, p=0.002). The effect was consistent across both scanner sites.

### Conclusions
Functional connectivity is a robust biomarker of working memory that generalizes across scanner manufacturers.
