# PITCH.md — RegCheck v1.1: A Hybrid Architecture for Scientific Integrity

## To the RegCheck Team

We have the deepest respect for what RegCheck accomplishes. The core design principles — human-in-the-loop, non-prescriptive dimensions, discipline-agnostic architecture — are the correct philosophical foundations for scientific auditing software.

This work preserves everything that makes RegCheck trustworthy while restructuring the internals around a different architectural idea: **compiling scientific documents into structured intermediate representations, then combining deterministic validation rules with LLM-based semantic reasoning.**

---

## The Core Idea

RegCheck v1 compares documents. It retrieves text chunks, embeds them, and uses an LLM to judge consistency. This works well and is a genuine contribution to scientific tooling.

RegCheck v1.1 proposes a complementary internal architecture:

> Compile each document into a **typed Scientific Contract** (a structured intermediate representation), represent it as a **protocol graph**, then detect deviations through a combination of **deterministic constraint validation**, **graph differencing**, and **LLM-based semantic reasoning** — all with **explicit uncertainty tracking** and **full evidence provenance**.

This separation makes the system more explainable (every deviation traces to a specific constraint or graph mutation), more extensible (domain-specific constraints can be registered as plugins), and better suited to detecting inferential deviations (e.g., statistical model changes, outcome switching) rather than only textual discrepancies.

---

## What We Built

### 1. Scientific Intermediate Representation

Each document is compiled into a typed Pydantic model:

```
Registration PDF  →  Protocol IR   (what was planned)
Publication PDF   →  Execution IR  (what was reported)
Evidence          →  Evidence IR   (supporting paragraphs, tables, figures)
```

Every extracted object — hypothesis, outcome, sample size, statistical analysis, claim — is a strict Pydantic model with full provenance tracking. This is not better text matching; it is structured compilation.

### 2. Pluggable Constraint Engine

Six core constraints are always evaluated:
- **C1**: Primary outcome equality (S5 if violated — outcome switching)
- **C2**: Sample size consistency (with dropout tolerance)
- **C3**: Analysis model compatibility
- **C4**: Hypothesis presence
- **C5**: Claim-to-hypothesis mapping
- **C6**: Exclusion criteria consistency

Each constraint returns **SATISFIED**, **VIOLATED**, or **UNCERTAIN**. The three-state logic is deliberate: scientific tools should be allowed to say "I don't know" when evidence is incomplete.

Domain-specific constraints are registered as plugins. We demonstrate this with two MRI-specific constraints (scanner parameter consistency, cross-vendor robustness checks). The same pattern supports Clinical Trial, ML Benchmark, or any other domain.

### 3. Graph Differencing with Semantic Drift Detection

Each IR is represented as a NetworkX protocol graph. The differ detects both structural mutations (node/edge changes) and semantic drift:
- **Inferential drift**: Analysis method changed for the same outcome
- **Evidence gap**: Claim with no supporting evidence in the graph
- **Outcome drift**: Measure changed despite same outcome ID

### 4. Multi-Axis Severity and Explicit Uncertainty

Every deviation is scored on four independent axes:
- Scientific Severity (S0–S5)
- Bias Risk (none → critical)
- Evidence Quality (insufficient → high)
- Confidence (how certain the system is)

Every object carries an `UncertaintyFlag` that can say "I don't know" with a reason and a suggested resolution action.

---

## What This Means for RegCheck

| Capability | RegCheck v1 | This Architecture |
|-----------|-------------|-------------------|
| Document representation | Text chunks | Typed IR (Pydantic models) |
| Comparison method | Embedding similarity | Constraint validation + graph diff |
| Deviation detection | LLM judges from retrieved text | Deterministic rules + LLM for ambiguous cases |
| Evidence tracking | Retrieved passages | Evidence graph with typed nodes and edges |
| Severity | Single score | Four independent axes |
| Uncertainty | Not explicit | Explicit flags with resolution suggestions |
| Domain adaptation | Different prompts | Constraint plugins |
| Explainability | LLM explanation | Provenance chain: Claim → Hypothesis → Outcome → Evidence |

---

## What We Did NOT Build (Deliberately)

- No parser ensemble — Docling + mock fallback. Parsing is important but not the novel contribution.
- No LLM ensemble — Single model with structured output.
- No GraphRAG — One protocol + one paper is not a corpus-level problem.
- No 20 agents — Five focused workflow nodes.

These are all valid engineering approaches, but they would distract from demonstrating the architectural idea.

---

## The Demonstration

We provide two case studies:

**Case Study 1: Clinical Trial** — A CBT for GAD RCT where the primary outcome is silently switched from GAD-7 to STAI (both anxiety measures with high text similarity), the analysis model is downgraded from ANCOVA to t-test, and exclusion criteria are tightened post-data. The constraint engine catches all three because it compares typed fields, not text embeddings.

**Case Study 2: Neuroimaging** — An fMRI study where scanner parameters (TR changed from 2000ms to 1500ms), cross-vendor robustness checks (silently dropped), and uncertainty quantification methods (downgraded from bootstrap + physics-informed to just p-values) are altered between registration and publication. Domain-specific constraint plugins catch these because they understand what MRI parameters mean.

---

## Next Steps

If this direction is interesting, three concrete next steps:

1. **Evaluate on real pairs** — 30 registration-publication pairs with human expert annotations, comparing this architecture against RegCheck v1 on false positive/negative rates and high-severity detection.
2. **Strengthen parsing** — Table extraction, numerical consistency, cross-references.
3. **Claim provenance visualization** — Interactive graph showing the full reasoning chain.

We welcome any feedback and are happy to adapt this work to fit RegCheck's roadmap.
