# Scientific Integrity Engine (SIE) - RegCheck_v1.1 Blueprint

## Architectural Vision
Transform RegCheck from flat RAG document comparison to neuro-symbolic constraint satisfaction.

**Pipeline:** Document → Parser Ensemble → Pydantic IR (Scientific Contract) → NetworkX Protocol Graph → LangGraph Multi-Agent Swarm → Severity-Weighted Audit Ledger.

**Core Paradigm Shift:**
```
RegCheck v1:  PDF → Chunks → Embeddings → Cosine Similarity → LLM Judgement
RegCheck v1.1:  PDF → Parser → Scientific IR → Protocol Graph → Graph Diff + Constraint Engine + Agents → Severity-Flagged Report
```

---

## Three Internal Representations (Key Innovation)

1. **Protocol IR** — What the study *planned* (from registration)
2. **Execution IR** — What the paper *actually reports* (from publication)
3. **Evidence IR** — Normalized links to supporting paragraphs, tables, figures, numerical values

Every deviation is a transformation between these IRs:
```
Protocol IR ──→ Execution IR ──→ Evidence IR
     │               │               │
     └─── Graph Diff ─┴── Constraint ─┘
                    Engine
```

This distinguishes: genuine protocol changes, reporting omissions, and insufficient evidence.

---

## Phase 1: Environment & Parsing Foundation
- [x] Project structure with `pyproject.toml`
- [x] `DocumentParser` interface (abstract base)
- [x] `DoclingParser` — IBM Docling for layout-aware Markdown + tables
- [x] `MockParser` — Pre-parsed Markdown fallback (never blocks downstream)
- [x] Parser benchmark harness

## Phase 2: Scientific Intermediate Representation (IR)
- [x] Core Pydantic models:
  - `Hypothesis` (id, description, type: primary/secondary)
  - `Outcome` (measure, timepoint, outcome_type)
  - `SampleSize` (planned_n, actual_n, exclusion_criteria)
  - `StatisticalAnalysisPlan` (model, covariates, corrections)
  - `ScientificClaim` (id, text, mapped_hypothesis_id)
  - `EvidenceSpan` (text, page, bbox, source_doc)
  - `DomainSpecificParameters` (extensible — MRI as first example)
- [x] `ScientificContract` root model (Protocol IR + Execution IR)
- [x] `ContractExtractor` using LLM structured output + Pydantic validation self-correction loop

## Phase 3: Protocol Graph + Graph Differencing
- [x] `ProtocolGraphBuilder` — NetworkX graph from ScientificContract
- [x] Node types: Hypothesis, Outcome, Parameter, Analysis, Claim, Evidence
- [x] Edge types: tested_by, constrained_by, measured_at, supported_by
- [x] `GraphDiffer` — Compare G_registration vs G_paper
- [x] Deterministic constraint checks (neuro-symbolic):
  - Sample size consistency (N_paper >= N_registration - epsilon)
  - Primary outcome presence
  - Analysis model compatibility
  - Claim-to-hypothesis mapping

## Phase 4: Multi-Agent Verification Workflow
- [x] LangGraph state machine with nodes:
  - `ContractExtractor` — Runs Phase 2/3
  - `GraphDiffNode` — Runs Phase 4 graph comparison
  - `ConstraintEngine` — Deterministic rule checks
  - `CriticAgent` — Self-reflects on deviations, flags false positives
  - `ReportGenerator` — Compiles final audit ledger
- [x] S0–S5 Deviation Severity Ontology:
  - S0: Trivial (wording changes)
  - S1: Administrative (author/date changes)
  - S2: Reporting Gap (missing parameters)
  - S3: Methodological (altered criteria, split leaks)
  - S4: Inferential (changed hypothesis/model)
  - S5: Bias-Critical (outcome switching, undocumented post-hoc)

## Phase 5: Report Generation & Demo
- [x] `LedgerGenerator` — Markdown report with severity flags
- [x] Editorial query template for deviations >= S3
- [x] Interactive CLI dashboard showing:
  - Side-by-side Registration Contract vs Publication Contract
  - Graph diff visualization
  - Severity-flagged deviations with evidence + suggested queries

---

## Technology Stack
| Layer | Technology |
|-------|-----------|
| Parsing | Docling (primary) + Mock fallback |
| Schemas | Pydantic v2 (strict) |
| Graph | NetworkX |
| Agents | LangGraph |
| LLMs | LiteLLM (pluggable: Claude, GPT, Gemini) |
| Structured Output | Instructor |
| Hybrid Retrieval | BM25 + Dense (stretch goal) |

## Non-Negotiable Principles
1. Human remains the final arbiter
2. Full provenance on every extracted object
3. Strict Pydantic typing everywhere — no free-form dicts
4. Domain-agnostic core with pluggable domain parameters
5. No overclaiming — flag uncertainty explicitly
