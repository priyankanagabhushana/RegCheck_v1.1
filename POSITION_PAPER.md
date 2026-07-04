# From Text Comparison to Scientific Contracts: A Hybrid Architecture for Automated Registration Auditing

**Research Positioning Document**

---

## Abstract

Current tools for comparing study registrations against publications rely on text chunking, embedding retrieval, and LLM-based similarity judgements. While effective for surface-level discrepancies, this approach struggles with inferential deviations (e.g., statistical model changes), dispersed evidence (e.g., results hidden in supplementary tables), and domain-specific parameters (e.g., MRI sequence specifications). We propose an alternative internal architecture based on three ideas: (1) compiling documents into typed Scientific Contracts rather than text chunks, (2) validating contracts against deterministic constraint rules before invoking LLM reasoning, and (3) tracking full evidence provenance through every deviation. We argue this separation — structured representation, deterministic validation, semantic reasoning — produces more explainable, extensible, and trustworthy scientific auditing tools.

---

## 1. The Problem with Text-Centric Auditing

RegCheck (Cummins et al., 2026) represents the current state of the art in automated registration-paper comparison. Its workflow — parse documents, chunk text, embed chunks, retrieve relevant passages, prompt an LLM to judge consistency — is pragmatic, modular, and effective for many use cases.

However, text-centric approaches face inherent limitations when the deviation is not textual:

**Inferential drift.** A registration specifies ANCOVA with three covariates. The publication reports a t-test with no covariates. Both passages discuss "statistical analysis" and "group differences." Cosine similarity between the methods sections would be high. The deviation is not in the words — it is in the analytical structure.

**Dispersed evidence.** A primary outcome is defined in the Methods section, reported in Table 3 (main text), and its sensitivity analysis appears in Supplementary Table S7. A text chunk retrieval system might find the Methods definition but miss the fact that Table 3 reports a different measure.

**Domain-specific parameters.** A neuroimaging registration specifies TR=2000ms, TE=30ms, and cross-vendor robustness checks. The publication reports TR=1500ms and silently drops the robustness checks. Both documents discuss "MRI acquisition parameters" in nearly identical prose. The deviation is in a numeric field that text similarity cannot reliably compare.

**Post-hoc claims.** A publication makes a claim about rumination reduction that cannot be traced to any hypothesis in the registration. Text similarity cannot detect the absence of a mapping — it can only compare what is present.

These are not edge cases. They represent the kinds of deviations that meta-science studies consistently find are common, often unreported, and consequential for the severity of statistical tests (Bakker et al., 2020; Claesen et al., 2021; TARG Meta-Research Group & Collaborators, 2023).

---

## 2. Three Architectural Ideas

### 2.1 Scientific Contracts (Structured Intermediate Representation)

Instead of chunking documents into 200-token segments, we propose compiling each document into a typed Scientific Contract: a Pydantic model that captures hypotheses, outcomes, sample sizes, statistical analyses, claims, and domain-specific parameters as structured objects with full provenance tracking.

Two instances of this model are created:
- **Protocol IR**: compiled from the registration (what was planned)
- **Execution IR**: compiled from the publication (what was reported)
- **Evidence IR**: a graph linking claims to supporting paragraphs, tables, figures, and numerical values

This is analogous to how a compiler transforms source code into an intermediate representation before optimization. The IR is not the output — it is the substrate on which all subsequent reasoning operates.

The key property is that every scientific object is a typed field with a known schema. Comparing `registration.outcomes[0].measure` against `publication.outcomes[0].measure` is a string equality check, not a similarity judgement. This eliminates the ambiguity that plagues text-based comparison.

### 2.2 Deterministic Constraint Validation

Before invoking any LLM, the system evaluates a set of formal constraints against the two IRs. Each constraint is an assertion that can be satisfied, violated, or uncertain:

- **C1 (Primary Outcome Equality)**: Registered primary outcomes must match publication primary outcomes. Violation severity: S5 (bias-critical).
- **C2 (Sample Size Consistency)**: Reported N must be ≥ planned N minus documented dropout. If dropout is undocumented, the result is *uncertain*, not *violated*.
- **C3 (Analysis Model Compatibility)**: Statistical models must match unless an amendment exists.
- **C4 (Hypothesis Presence)**: Every registered hypothesis must appear in the publication.
- **C5 (Claim-Hypothesis Mapping)**: Every publication claim must trace to a registered hypothesis.
- **C6 (Exclusion Criteria Consistency)**: Exclusion criteria should not be tightened post-data.

The three-state logic (satisfied / violated / uncertain) is deliberate. Scientific tools should be allowed to say "I don't know" when the evidence is incomplete. This is more honest than forcing a binary judgement and more useful than returning a confidence score — it tells the reviewer exactly what additional information would resolve the uncertainty.

Constraints are pluggable. Domain-specific rules (e.g., MRI scanner parameter consistency, cross-vendor robustness verification) are registered as plugins without modifying the core engine. This follows the Open-Closed Principle and enables the architecture to grow with new domains.

### 2.3 Evidence Provenance Chains

Every deviation, claim, and conclusion is linked to its supporting evidence through a typed graph:

```
Claim → Hypothesis → Outcome → Statistical Analysis → Evidence Span
```

A reviewer can trace any finding backward through the reasoning chain: which hypothesis does this claim test? Which outcome supports it? Which table contains the relevant statistic? Where in the original registration was this specified?

This provenance tracking serves two purposes. First, it makes the system explainable — every output has a visible audit trail. Second, it enables a new class of checks that text comparison cannot perform: detecting claims that cannot be traced to any registered hypothesis, or identifying outcomes that exist in the registration but have no supporting evidence in the publication.

---

## 3. The Hybrid Approach

The architecture combines three reasoning modes:

1. **Deterministic rules** handle unambiguous cases (sample size arithmetic, primary outcome identity, hypothesis presence). These are fast, explainable, and never hallucinate.

2. **Graph differencing** detects structural changes (nodes added or removed, attributes changed) and semantic drift (inferential drift, evidence gaps, methodological drift). These are also deterministic but operate on the compiled representation rather than raw text.

3. **LLM-based reasoning** handles genuinely ambiguous cases — interpreting the meaning of a deviation, assessing its likely impact, generating editorial queries for authors. The LLM operates on the structured IR and constraint results, not on raw text chunks.

This separation means the LLM is invoked only where its strengths (language understanding, nuance, ambiguity resolution) are needed, and deterministic methods handle everything that can be precisely specified. The result is a system that is both more accurate (for cases where rules apply) and more honest (for cases where they don't).

---

## 4. Why This Matters for RegCheck

RegCheck's core design principles — human-in-the-loop, non-prescriptive dimensions, discipline-agnostic architecture — are correct and should be preserved. The question is whether the internal architecture can be restructured to make these principles more powerful.

We believe it can, in three specific ways:

**Explainability.** When RegCheck reports a deviation, the reviewer sees retrieved text passages and an LLM judgement. With the proposed architecture, the reviewer sees: the specific constraint violated, the typed fields that differ, the evidence provenance chain, and an explicit uncertainty assessment. This gives reviewers the information they need to make their own judgement, which is the stated goal of the human-in-the-loop design.

**Extensibility.** Adding domain-specific comparison logic to RegCheck requires modifying prompts. With the constraint registry, domain experts write self-contained constraint classes that are evaluated against the structured IR. This is a fundamentally different extensibility model — one that scales with the community rather than requiring centralized prompt engineering.

**Evaluation.** Because every deviation is linked to a specific constraint and a specific typed field, it becomes possible to evaluate the system's performance at a granular level: which constraints produce false positives? Which produce false negatives? Where does the LLM improve on the rules, and where does it introduce noise? This enables the kind of systematic evaluation that RegCheck's authors are rightly pursuing.

---

## 5. Limitations and Honest Assessment

This architecture has real limitations that must be acknowledged:

**Parsing quality is the bottleneck.** The structured IR is only as good as the extraction. If the LLM misidentifies a primary outcome or misses a statistical analysis, all downstream reasoning inherits that error. Improving parsing robustness — especially for tables, figures, and numerical values — is the highest-priority technical work.

**The LLM is still needed for extraction.** Even with structured output and Pydantic validation, the initial compilation from raw text to typed IR relies on an LLM. This is a fundamental dependency that cannot be eliminated with current technology.

**Evaluation is incomplete.** We have 44 passing unit tests and two synthetic case studies. We do not yet have systematic evaluation on real registration-publication pairs with human expert annotations. This is the most important missing piece.

**The constraint language is still Python.** A more formal constraint specification language (closer to a DSL) would make constraints more readable and auditable by non-programmers. This is future work.

---

## 6. Contribution

This work contributes:

1. A typed Scientific Intermediate Representation for compiled registration and publication documents, with full provenance tracking.
2. A pluggable constraint engine that evaluates formal assertions against structured IRs with three-state logic (satisfied / violated / uncertain).
3. A hybrid reasoning architecture that combines deterministic rules, graph differencing, and LLM-based semantic reasoning.
4. Two case studies (clinical trial, neuroimaging) demonstrating domain-agnostic and domain-specific deviation detection.
5. An open-source implementation backed by 44 passing tests.

We do not claim this is a finished system. We claim it is a credible architectural direction that preserves the philosophical foundations of RegCheck while enabling capabilities that text-centric approaches cannot easily support.

---

## References

- Bakker, M., et al. (2020). Ensuring the quality and specificity of preregistrations. *PLOS Biology*, 18(12), e3000937.
- Claesen, A., et al. (2021). Comparing dream to reality: an assessment of adherence of the first generation of preregistered studies. *Royal Society Open Science*, 8(10), 211037.
- Cummins, J., et al. (2026). RegCheck: A tool for automating comparisons between study registrations and papers. *arXiv:2601.13330*.
- Goldacre, B., et al. (2019). COMPare: a prospective cohort study correcting and monitoring 58 misreported trials in real time. *Trials*, 20(1), 118.
- Lakens, D. (2024). When and How to Deviate From a Preregistration. *Collabra: Psychology*, 10(1), 117094.
- TARG Meta-Research Group & Collaborators (2023). Estimating the prevalence of discrepancies between study registrations and publications. *Systematic Reviews*.
