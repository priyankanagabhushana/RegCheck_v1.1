# RegCheck v1.1

RegCheck v1.1 is a research prototype for comparing study registrations,
regulatory guidance, and published reports. It combines structured extraction,
domain-specific validation, graph-based comparison, and a Streamlit interface.

## What this version contributes

- A typed `ScientificContract` intermediate representation for registrations and
  publications.
- Explicit comparison of design, outcomes, analysis, sample size, and MRI
  parameters.
- Evidence-aware extraction fields that preserve source references and
  uncertainty flags.
- A deterministic constraint engine alongside LLM-assisted extraction and
  critique.
- A small evaluation harness with named synthetic scenarios and a documented
  evaluation mode.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
streamlit run app.py
```

The application login requires both `REGCHECK_USERNAME` and
`REGCHECK_PASSWORD`. The app refuses authentication when either variable is
missing; do not use real credentials in a shared demo environment.

## Evaluation scope

The default evaluation suite is intentionally described as
`synthetic_contracts`. It tests whether known, scenario-specific changes in
typed contracts produce the expected graph differences and severity labels.
It does **not** estimate full PDF extraction accuracy, LLM classification
accuracy, or end-to-end agreement with expert annotations. The evaluation
limitations and the path for adding real annotated documents are documented in
[`evaluation/README.md`](evaluation/README.md).

## Project direction

This repository is strongest as an interpretable research prototype: its
contract schema, deterministic checks, and domain plugins make reasoning about
why a deviation was flagged straightforward. Jamie Cummins' upstream RegCheck
is more mature as a production service, particularly around evidence
localization, API/authentication, report ownership, deployment, and operational
testing. The two projects should therefore be presented as complementary, not
as a claim that this prototype replaces the upstream system.
