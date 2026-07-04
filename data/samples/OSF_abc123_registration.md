# Registration: Functional Connectivity Predicts Working Memory Performance — A Multi-Site fMRI Study

## OSF Registration: osf.io/abc123

## Hypotheses
H1 (Primary): DLPFC-PPC functional connectivity strength will positively predict working memory accuracy (direction: greater).
H2 (Secondary): Connectivity-behavior relationships will be consistent across Siemens and GE scanners.

## Primary Outcomes
- O1: DLPFC-PPC functional connectivity (Fisher z-transformed), measured at baseline scan
- O2: N-back task accuracy (2-back condition), measured in-scanner

## Sample Size
- Planned N: 120 participants
- Power analysis: Power=0.85, alpha=0.05, r=0.30, two-tailed
- Expected dropout: 10%

## MRI Acquisition Parameters
- Scanner field strength: 3.0 Tesla
- Repetition time (TR): 2000ms
- Echo time (TE): 30ms
- Voxel size: 2.0 x 2.0 x 2.0 mm
- Sequence: Gradient-echo EPI (fMRI BOLD)
- Region of interest: DLPFC and PPC (bilateral)

## Preprocessing Pipeline
fMRIPrep 23.1.0 with ICA-AROMA denoising. Cross-vendor robustness checks will be performed by comparing results between Siemens and GE scanners.

## Uncertainty Quantification
Bootstrap confidence intervals (1000 resamples) with physics-informed signal-to-noise estimation.

## Exclusion Criteria
- Head motion > 3mm translation or 3° rotation
- History of neurological or psychiatric disorder
- Contraindications for MRI

## Analysis Plan
SA1: Mixed-effects regression with WM_accuracy as DV, connectivity + scanner_vendor + age + sex as IVs, site + head_motion_fd as covariates. Software: FSL 6.0 + Python Nilearn.
SA2: Permutation testing (5000 permutations) for connectivity-behavior correlation. FDR correction (q<0.05).
