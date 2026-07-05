"""Contract Extractor - Compiles parsed documents into ScientificContract IR.

Uses LLM structured output (via instructor or native Pydantic validation)
with a self-correction loop on validation errors.

Classification strategy (defense in depth):
    1. Deterministic pre-classifier (keyword heuristics, zero cost)
    2. LLM classifier (if pre-classifier is uncertain)
    3. Post-extraction sanity check (reject hallucinated clinical fields)

The default is 'other' (fail closed), NOT 'clinical_trial' (fail open).
A false negative on a clinical trial is recoverable (user can override).
A false positive on regulatory guidance produces 41 hallucinated deviations.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from parsers.base import ParsedDocument
from schemas.ir import (
    DomainSpecificParameters,
    EvidenceSpan,
    ExclusionCriterion,
    FieldStatus,
    Hypothesis,
    HypothesisType,
    Outcome,
    OutcomeType,
    SampleSize,
    ScientificClaim,
    ScientificContract,
    ScientificAnalysis as StatisticalAnalysis,
    UncertaintyFlag,
)

logger = logging.getLogger(__name__)


# ───────────────────────────── Deterministic Pre-Classifier ─────────────────────────────

# Phrases that strongly indicate a document is NOT a clinical trial.
# These appear in titles, headers, or first paragraphs of guidance/regulatory docs.
_NON_TRIAL_SIGNALS = [
    "guidance for industry",
    "guidance for fda staff",
    "guidance document",
    "fda guidance",
    "ema guidance",
    "regulatory guidance",
    "criteria for significant risk",
    "significant risk investigations",
    "contains nonbinding recommendations",
    "this guidance describes",
    "this guidance document",
    "draft guidance",
    "final guidance",
    "points to consider",
    "concept paper",
    "regulatory framework",
    "this document supersedes",
    "does not establish legally enforceable",
    "guidances describe the agency",
    "least burdensome approach",
    "device classification",
    "510(k) guidance",
    "premarket approval guidance",
    "de novo classification",
    "advisory committee",
    "food and drug administration",
]

# Phrases that strongly indicate a document IS a clinical trial.
_TRIAL_SIGNALS = [
    "randomized controlled trial",
    "randomised controlled trial",
    "clinical trial",
    "clinical study",
    "study protocol",
    "randomization",
    "randomisation",
    "informed consent",
    "institutional review board",
    "irb approval",
    "ethics committee",
    "primary endpoint",
    "secondary endpoint",
    "sample size calculation",
    "power analysis",
    "inclusion criteria",
    "exclusion criteria",
    "enrollment",
    "enrolment",
    "participants were recruited",
    "nct0",
    "isrctn",
    "actrn",
]


def _preclassify_document(markdown: str) -> Optional[str]:
    """Deterministic pre-classifier using keyword heuristics.

    Returns a classification if confident, or None if uncertain.
    This runs BEFORE the LLM classifier and costs zero API calls.

    Strategy:
        - Count non-trial signals vs trial signals in the first 3000 chars.
        - If non-trial signals dominate (>=3 and more than trial signals),
          return 'regulatory_guidance' or 'other' immediately.
        - If trial signals dominate, return 'clinical_trial'.
        - If neither dominates, return None (let LLM decide).
    """
    text = markdown[:5000].lower()

    non_trial_count = sum(1 for s in _NON_TRIAL_SIGNALS if s in text)
    trial_count = sum(1 for s in _TRIAL_SIGNALS if s in text)

    # Strong non-trial signal: regulatory guidance language
    if non_trial_count >= 3 and non_trial_count > trial_count:
        # Check if it's specifically FDA/regulatory guidance
        if any(s in text for s in ["guidance for industry", "fda guidance", "criteria for significant risk",
                                    "contains nonbinding recommendations", "regulatory guidance"]):
            logger.info(
                f"Pre-classifier: regulatory_guidance "
                f"(non_trial={non_trial_count}, trial={trial_count})"
            )
            return "regulatory_guidance"
        logger.info(
            f"Pre-classifier: other (non_trial={non_trial_count}, trial={trial_count})"
        )
        return "other"

    # Strong trial signal: clinical trial language with no regulatory signals
    if trial_count >= 4 and trial_count > non_trial_count * 2:
        logger.info(
            f"Pre-classifier: clinical_trial "
            f"(trial={trial_count}, non_trial={non_trial_count})"
        )
        return "clinical_trial"

    # Uncertain — let the LLM classifier decide
    logger.info(
        f"Pre-classifier: uncertain (trial={trial_count}, non_trial={non_trial_count})"
    )
    return None


DOCUMENT_CLASSIFICATION_PROMPT = """Classify this document into exactly one category. Return ONLY the category name, nothing else.

Categories:
- clinical_trial: A study with human participants, pre-registered outcomes, hypotheses, sample sizes, arms, statistical analyses. The document describes an actual experiment or study that was conducted or planned.
- regulatory_guidance: An FDA/EMA/regulatory guidance document that defines thresholds, criteria, or standards. This is NOT a study — it is a policy document that tells researchers what rules to follow.
- research_protocol: A detailed protocol for a study with methods, procedures, schedules, enrollment targets
- other: Any other document type (review papers, editorials, commentaries, policy documents)

IMPORTANT: A table of safety thresholds or operating conditions is NOT a set of hypotheses.
A document that says "Guidance for Industry" is NOT a clinical trial.
A document that lists SAR limits or magnetic field strength thresholds is regulatory guidance.

Document content (first 3000 chars):
{preview}

Category:"""


EXTRACTION_SYSTEM_PROMPT = """You are a scientific document analyst. Your task is to extract structured information from a scientific document into a precise JSON format.

CRITICAL RULES — follow these exactly:
1. Extract ONLY information explicitly stated in the document. Every extracted object MUST have at least one evidence span with the exact text from the source.
2. If you cannot find a direct quote supporting a field, that field MUST be null or empty. NEVER invent data.
3. A regulatory guidance or policy document has NO hypotheses, NO outcomes, NO sample sizes. Return empty for all.
4. A table of thresholds is NOT a list of hypotheses. Do not convert table rows into hypotheses.
5. For each hypothesis, outcome, or analysis you extract, you MUST include evidence: [{"text": "exact quoted text from document", "source_doc": "[registration|publication]", "section": "Methods/Para 3"}]
6. If no evidence text exists for a field, do not create the object — return empty list.
7. Be skeptical: if you're unsure whether something counts as a hypothesis, it probably doesn't. Err on the side of empty.
8. RESPECT THE RETRIEVAL HINTS: If the retrieval analysis says "NOT FOUND" for a field, that field MUST be empty. Do NOT try to find content that the retrieval could not find.

Output a JSON object matching the ScientificContract schema."""

EXTRACTION_USER_PROMPT = """Extract the structured scientific information from this document.

Document type: {doc_type}
Document ID: {doc_id}

{retrieval_hints}

Document content:
{markdown}

{tables_section}

Return a JSON object with these fields:
- doc_id: "{doc_id}"
- doc_type: "{doc_type}"
- title: document title
- authors: list of author names
- doi: DOI if present
- registration_id: registration ID if present (e.g., ClinicalTrials.gov)
- hypotheses: list of {{id, description, hypothesis_type, variables, direction, status, evidence: [{{text, source_doc, section}}]}}
- outcomes: list of {{id, measure, timepoint, outcome_type, description, status, evidence: [{{text, source_doc, section}}]}}
- sample_size: {{planned_n, actual_n, power_analysis, dropout_rate, justification, status, evidence: [{{text, source_doc, section}}]}}
- exclusion_criteria: list of {{id, description, criterion_type, evidence: [{{text, source_doc}}]}}
- analyses: list of {{id, model, dependent_variable, independent_variables, covariates, corrections, software, evidence: [{{text, source_doc}}]}}
- claims: list of {{id, text, mapped_hypothesis_id, strength, supporting_evidence: [{{text, source_doc}}]}}

status field values: "present" (extracted from doc), "missing" (expected but absent), "low_evidence" (found but weak), "not_applicable" (field doesn't apply)
Every extracted object MUST have at least one evidence span with exact text.
If the retrieval analysis says a field is NOT FOUND, set its status to "missing" and return an empty list for it.
Return ONLY the JSON object, no other text."""


# ───────────────────────────── Field-Level Evidence Retrieval ─────────────────────────────

# Keywords that indicate relevant content for each field type
_FIELD_RETRIEVAL_PATTERNS = {
    "hypotheses": {
        "keywords": [
            "hypothesize", "hypothesis", "hypotheses", "we predict", "we hypothesize",
            "primary hypothesis", "secondary hypothesis", "aim", "objective",
            "we expect", "we postulate", "research question",
        ],
        "anti_keywords": [
            "guidance for industry", "regulatory", "significant risk",
            "contains nonbinding", "operating condition",
        ],
    },
    "outcomes": {
        "keywords": [
            "primary outcome", "secondary outcome", "primary endpoint", "secondary endpoint",
            "outcome measure", "outcome measure", "efficacy endpoint", "safety endpoint",
            "primary measure", "secondary measure", "outcome variable",
            "gad-7", "phq-9", "beck depression", "Hamilton", "STAI",
            "pain score", "quality of life", "SF-36", "EQ-5D",
        ],
        "anti_keywords": [
            "guidance for industry", "regulatory", "significant risk",
        ],
    },
    "sample_size": {
        "keywords": [
            "sample size", "sample size calculation", "power analysis", "power calculation",
            "planned enrollment", "target enrollment", "planned n", "target n",
            "number of participants", "number of subjects", "recruitment target",
            "effect size", "alpha level", "significance level",
        ],
        "anti_keywords": [
            "guidance for industry", "regulatory",
        ],
    },
    "analyses": {
        "keywords": [
            "statistical analysis", "statistical model", "analysis plan",
            "anova", "ancova", "t-test", "chi-square", "regression",
            "mixed model", "linear model", "logistic regression",
            "cox proportional", "kaplan-meier", "wilcoxon", "mann-whitney",
            "multiple comparison", "bonferroni", "holm", "fdr",
            "intention to treat", "per protocol", "sensitivity analysis",
            "covariate", "adjusted model", "unadjusted model",
        ],
        "anti_keywords": [
            "guidance for industry", "regulatory",
        ],
    },
    "exclusion_criteria": {
        "keywords": [
            "exclusion criteria", "inclusion criteria", "eligibility criteria",
            "inclusion and exclusion", "eligibility", "inclusion criterion",
            "exclusion criterion", "inclusion/exclusion",
            "participants were eligible", "participants were included",
            "participants were excluded",
        ],
        "anti_keywords": [
            "guidance for industry", "regulatory",
        ],
    },
    "claims": {
        "keywords": [
            "we found", "our results show", "we demonstrate", "we conclude",
            "treatment resulted in", "intervention led to", "significant difference",
            "no significant difference", "p <", "p =", "p < 0.05", "p < 0.01",
            "effect size", "confidence interval", "odds ratio", "risk ratio",
            "our findings suggest", "these results indicate",
        ],
        "anti_keywords": [
            "guidance for industry", "regulatory",
        ],
    },
}


def _retrieve_field_evidence(markdown: str, field_type: str) -> dict:
    """Retrieve evidence for a specific field type from document text.

    Returns a dict with:
        - found: bool (whether relevant text was found)
        - passages: list[str] (relevant text passages, up to 3)
        - confidence: float (0-1, how confident we are that this field exists)
    """
    text_lower = markdown.lower()
    patterns = _FIELD_RETRIEVAL_PATTERNS.get(field_type, {})

    keywords = patterns.get("keywords", [])
    anti_keywords = patterns.get("anti_keywords", [])

    # Check for anti-keywords first (signals this is NOT a clinical trial)
    anti_count = sum(1 for ak in anti_keywords if ak in text_lower)
    if anti_count >= 2:
        return {"found": False, "passages": [], "confidence": 0.0}

    # Find passages containing relevant keywords
    passages = []
    matched_keywords = set()

    for kw in keywords:
        if kw in text_lower:
            matched_keywords.add(kw)
            # Extract surrounding context (up to 300 chars around the match)
            idx = text_lower.find(kw)
            while idx >= 0 and len(passages) < 5:
                start = max(0, idx - 100)
                end = min(len(markdown), idx + len(kw) + 200)
                passage = markdown[start:end].strip()
                if passage and passage not in passages:
                    passages.append(passage)
                idx = text_lower.find(kw, idx + 1)

    # Calculate confidence based on number of keyword matches
    if not matched_keywords:
        return {"found": False, "passages": [], "confidence": 0.0}

    confidence = min(1.0, len(matched_keywords) / 3.0)  # 3+ keywords = high confidence

    return {
        "found": True,
        "passages": passages[:3],  # Top 3 most relevant passages
        "confidence": confidence,
        "matched_keywords": list(matched_keywords),
    }


def _build_retrieval_hints(markdown: str) -> str:
    """Build retrieval hints for the extraction prompt.

    For each field type, determines whether relevant evidence exists in the
    document and includes this information in the prompt. This prevents the
    LLM from hallucinating fields that have no supporting evidence.

    This is the core of the evidence-guided extraction architecture:
    retrieval happens BEFORE extraction, not after.
    """
    field_types = ["hypotheses", "outcomes", "sample_size", "analyses", "exclusion_criteria", "claims"]
    hints = ["RETRIEVAL ANALYSIS (evidence search results for each field type):"]

    for field in field_types:
        result = _retrieve_field_evidence(markdown, field)
        if result["found"]:
            keywords = ", ".join(result.get("matched_keywords", [])[:5])
            hints.append(f"- {field}: FOUND (keywords: {keywords})")
            if result["passages"]:
                hints.append(f"  Relevant text: \"{result['passages'][0][:200]}...\"")
        else:
            hints.append(f"- {field}: NOT FOUND — set status to 'missing', return empty list")

    hints.append("")
    hints.append("IMPORTANT: For any field marked NOT FOUND, you MUST return an empty list and set status to 'missing'.")
    hints.append("Do NOT attempt to extract content for fields where the retrieval found no evidence.")
    hints.append("")

    return "\n".join(hints)


class ContractExtractor:
    """Extracts ScientificContract from parsed documents using LLM structured output.

    Implements a self-correction loop: if LLM output fails Pydantic validation,
    the ValidationError is fed back to the LLM to fix the schema violation.

    Model configuration is set via constructor or the REGCHECK_MODEL env var.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        max_chars: int = 50000,
    ):
        import os

        self.model = model or os.environ.get("REGCHECK_MODEL", "gpt-4o")
        self.max_retries = max_retries
        self.api_key = api_key
        self.max_chars = max_chars

    def extract(self, parsed: ParsedDocument, doc_type: str = "registration") -> ScientificContract:
        """Extract a ScientificContract from a ParsedDocument.

        First classifies the document type. If the document is not a clinical trial
        (e.g., FDA guidance, regulatory document), returns a minimal contract with
        uncertainty flags. This prevents hallucination of hypotheses/outcomes from
        non-trial documents.

        Args:
            parsed: The parsed document output
            doc_type: Either 'registration' or 'publication'

        Returns:
            Validated ScientificContract
        """
        doc_id = f"{doc_type}_{Path(parsed.source_path).stem}"

        # CT.gov JSON is already structured clinical trial data — skip classification
        if parsed.parser_name == "ctgov_json":
            doc_category = "clinical_trial"
            logger.info(f"CT.gov JSON detected, skipping classification ({doc_id})")
        else:
            # Classify document type first to prevent hallucination
            doc_category = self._classify_document(parsed)
            logger.info(f"Document classified as: {doc_category} ({doc_id})")

        if doc_category != "clinical_trial":
            return self._create_non_trial_contract(doc_id, doc_type, parsed, doc_category)

        tables_section = ""
        if parsed.tables:
            tables_section = "Tables found in document:\n" + "\n\n".join(
                f"Table {i+1}:\n{t}" for i, t in enumerate(parsed.tables)
            )

        markdown_content = parsed.markdown
        truncated = len(markdown_content) > self.max_chars
        if truncated:
            markdown_content = markdown_content[:self.max_chars]
            logger.warning(
                f"Document truncated from {len(parsed.markdown)} to {self.max_chars} chars "
                f"for LLM context ({parsed.source_path})"
            )

        # Evidence-guided retrieval: determine which fields have evidence BEFORE extraction
        retrieval_hints = _build_retrieval_hints(markdown_content)
        logger.info(f"Retrieval hints for {doc_id}:\n{retrieval_hints}")

        user_prompt = EXTRACTION_USER_PROMPT.format(
            doc_type=doc_type,
            doc_id=doc_id,
            markdown=markdown_content,
            tables_section=tables_section,
            retrieval_hints=retrieval_hints,
        )

        return self._extract_with_retry(user_prompt, doc_id, doc_type, parsed.markdown, doc_category)

    def _extract_with_retry(
        self, prompt: str, doc_id: str, doc_type: str, raw_markdown: str,
        doc_category: str = "clinical_trial",
    ) -> ScientificContract:
        """Extract with self-correction loop on validation errors."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                raw_json = self._call_llm(prompt)
                contract = ScientificContract.model_validate(raw_json)
                contract.doc_id = doc_id
                contract.doc_type = doc_type
                contract.raw_markdown = raw_markdown
                contract = self._verify_extraction_evidence(contract)
                contract = self._enforce_retrieval_results(contract, raw_markdown)
                contract = self._validate_extraction_sanity(contract, doc_category)
                logger.info(
                    f"Successfully extracted contract for {doc_id}: "
                    f"{contract.summary_stats()}"
                )
                return contract

            except ValidationError as e:
                last_error = e
                prompt = f"{prompt}\n\nValidation error: {e}\nFix and return valid JSON."

        raise ValueError(
            f"Failed to extract valid ScientificContract after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

    def _verify_extraction_evidence(self, contract: ScientificContract) -> ScientificContract:
        """Post-extraction evidence quality check.

        For every extracted field (hypotheses, outcomes, analyses, claims),
        verify that at least one evidence span exists with actual text content.
        If no evidence exists, the field is downgraded: extraction_confidence
        is reduced and uncertainty is flagged.

        This catches hallucinated extractions where the LLM returned objects
        without actual source text — the primary cause of false deviations
        on non-clinical-trial documents.
        """
        total_objects = 0
        objects_without_evidence = 0

        for obj_list, name in [
            (contract.hypotheses, "hypothesis"),
            (contract.outcomes, "outcome"),
            (contract.analyses, "analysis"),
            (contract.claims, "claim"),
        ]:
            for obj in obj_list:
                total_objects += 1
                if hasattr(obj, "evidence") and obj.evidence:
                    has_text = any(e.text and e.text.strip() for e in obj.evidence)
                    if not has_text:
                        objects_without_evidence += 1
                        obj.uncertainty.is_uncertain = True
                        obj.uncertainty.reason = (
                            f"{name} '{getattr(obj, 'id', '?')}' has no supporting evidence text — "
                            "may be hallucinated"
                        )
                else:
                    objects_without_evidence += 1

        if total_objects > 0:
            evidence_ratio = 1.0 - (objects_without_evidence / total_objects)
            contract.extraction_confidence = min(contract.extraction_confidence or 1.0, evidence_ratio)

            if evidence_ratio < 0.5:
                contract.overall_uncertainty.is_uncertain = True
                contract.overall_uncertainty.reason = (
                    f"Only {evidence_ratio:.0%} of extracted objects have supporting evidence. "
                    f"{objects_without_evidence}/{total_objects} objects may be hallucinated."
                )

        return contract

    def _validate_extraction_sanity(
        self, contract: ScientificContract, doc_category: str
    ) -> ScientificContract:
        """Post-extraction sanity check: reject extractions that don't make sense.

        If a document was classified as non-trial but the LLM still extracted
        clinical trial fields, this method flags the entire contract as uncertain.

        If a document was classified as clinical_trial but has suspicious
        characteristics (many hypotheses with no direction, no outcomes despite
        many hypotheses), the contract is flagged.

        This is the last line of defense against schema-forced hallucination.
        """
        # Case 1: Document is non-trial but has clinical fields — reject
        if doc_category in ("regulatory_guidance", "other"):
            clinical_fields = (
                len(contract.hypotheses) + len(contract.outcomes)
                + len(contract.analyses)
            )
            if clinical_fields > 0:
                logger.warning(
                    f"Sanity check: {doc_category} document has {clinical_fields} "
                    f"clinical fields extracted — likely hallucinated. Clearing."
                )
                contract.hypotheses = []
                contract.outcomes = []
                contract.analyses = []
                contract.claims = []
                contract.exclusion_criteria = []
                contract.sample_size = None
                contract.extraction_confidence = 0.0
                contract.overall_uncertainty.is_uncertain = True
                contract.overall_uncertainty.reason = (
                    f"Document classified as '{doc_category}' but the extractor "
                    f"produced clinical trial fields. These were likely hallucinated "
                    f"from regulatory thresholds or policy language. Cleared to "
                    f"prevent false deviations."
                )
                contract.overall_uncertainty.resolution_suggestion = (
                    "This document is not a clinical trial. Use structural "
                    "comparison for regulatory guidance documents."
                )

        # Case 2: Clinical trial with suspicious extraction patterns
        if doc_category == "clinical_trial":
            n_hyp = len(contract.hypotheses)
            n_out = len(contract.outcomes)

            # Many hypotheses but zero outcomes — suspicious
            if n_hyp >= 5 and n_out == 0:
                logger.warning(
                    f"Sanity check: {n_hyp} hypotheses but 0 outcomes — "
                    f"suspicious extraction. Flagging as uncertain."
                )
                contract.overall_uncertainty.is_uncertain = True
                contract.overall_uncertainty.reason = (
                    f"Extracted {n_hyp} hypotheses but 0 outcomes. "
                    f"This pattern suggests the extractor may have "
                    f"misidentified non-clinical content as hypotheses."
                )

            # Check for hypotheses that look like regulatory thresholds
            threshold_pattern = re.compile(
                r'(greater than|less than|equal to|exceed|threshold|limit|'
                r'w/kg|tesla|db\b|dBA|dB/dt)',
                re.IGNORECASE
            )
            threshold_hyps = [
                h for h in contract.hypotheses
                if threshold_pattern.search(h.description)
            ]
            if len(threshold_hyps) >= 3:
                logger.warning(
                    f"Sanity check: {len(threshold_hyps)} hypotheses match "
                    f"regulatory threshold patterns — likely misclassified."
                )
                # Clear these as they're probably regulatory thresholds, not hypotheses
                contract.hypotheses = [
                    h for h in contract.hypotheses if h not in threshold_hyps
                ]
                for h in threshold_hyps:
                    logger.info(f"  Removed threshold-like hypothesis: {h.description[:80]}")

        return contract

    def _enforce_retrieval_results(
        self, contract: ScientificContract, markdown: str
    ) -> ScientificContract:
        """Enforce retrieval results: remove fields that retrieval said weren't found.

        This is the enforcement layer of evidence-guided extraction. Even if the
        LLM hallucinated content for a field that retrieval determined had no
        evidence, this method removes it.

        This prevents the scenario where:
            1. Retrieval says "hypotheses: NOT FOUND"
            2. LLM ignores this and extracts hypotheses anyway
            3. Constraint engine compares hallucinated hypotheses → false deviations
        """
        field_checks = [
            ("hypotheses", "hypotheses"),
            ("outcomes", "outcomes"),
            ("analyses", "analyses"),
            ("claims", "claims"),
            ("exclusion_criteria", "exclusion_criteria"),
        ]

        for field_type, attr_name in field_checks:
            result = _retrieve_field_evidence(markdown, field_type)
            if not result["found"]:
                current = getattr(contract, attr_name)
                if current:
                    logger.info(
                        f"Retrieval enforcement: clearing {len(current)} {field_type} "
                        f"(retrieval found no evidence)"
                    )
                    setattr(contract, attr_name, [])

        # Special handling for sample_size
        ss_result = _retrieve_field_evidence(markdown, "sample_size")
        if not ss_result["found"] and contract.sample_size:
            # Only clear if sample_size was extracted but retrieval found no evidence
            if contract.sample_size.planned_n or contract.sample_size.actual_n:
                logger.info(
                    "Retrieval enforcement: clearing sample_size "
                    "(retrieval found no evidence)"
                )
                contract.sample_size = None

        return contract

    def _call_llm(self, prompt: str) -> dict:
        """Call the LLM and parse JSON response.

        Uses instructor for structured output if available, falls back to raw LLM call.
        """
        try:
            return self._call_with_instructor(prompt)
        except ImportError:
            return self._call_with_litellm(prompt)

    def _call_with_instructor(self, prompt: str) -> dict:
        """Use instructor for structured output extraction."""
        import instructor
        from litellm import completion

        client = instructor.from_litellm(completion)

        response = client.chat.completions.create(
            model=self.model,
            response_model=ScientificContract,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_retries=self.max_retries,
        )

        return response.model_dump()

    def _call_with_litellm(self, prompt: str) -> dict:
        """Fallback: raw LLM call with manual JSON parsing."""
        from litellm import completion

        response = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        return json.loads(content)

    def _classify_document(self, parsed: ParsedDocument) -> str:
        """Classify document type to prevent hallucination on non-trial documents.

        Defense in depth:
            1. Deterministic pre-classifier (keyword heuristics, zero cost)
            2. LLM classifier (if pre-classifier is uncertain)
            3. Default to 'other' on ANY failure (fail closed, not open)

        A false negative on a clinical trial is recoverable — the user sees
        "classified as other" and can retry. A false positive on regulatory
        guidance produces 41 hallucinated deviations. Fail closed.
        """
        # Layer 1: Deterministic pre-classifier
        pre_result = _preclassify_document(parsed.markdown)
        if pre_result is not None:
            return pre_result

        # Layer 2: LLM classifier
        preview = parsed.markdown[:3000]
        prompt = DOCUMENT_CLASSIFICATION_PROMPT.format(preview=preview)

        try:
            from litellm import completion
            resp = completion(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Classify documents. Return exactly one word."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                max_tokens=10,
            )
            category = resp.choices[0].message.content.strip().lower()
            # Normalize common variations
            category = category.replace("-", "_").replace(" ", "_")
            valid = {"clinical_trial", "regulatory_guidance", "research_protocol", "other"}
            if category in valid:
                return category
            # Partial match: "regulatory" → "regulatory_guidance"
            if "guidance" in category or "regulatory" in category:
                return "regulatory_guidance"
            if "trial" in category or "study" in category:
                return "clinical_trial"
            logger.warning(f"Unknown category '{category}', defaulting to 'other'")
            return "other"
        except Exception as e:
            logger.warning(f"Document classification failed: {e}, defaulting to 'other'")
            return "other"

    def _create_non_trial_contract(
        self, doc_id: str, doc_type: str, parsed: ParsedDocument, category: str
    ) -> ScientificContract:
        """Create a minimal contract for non-trial documents.

        Returns a contract with all scientific fields empty and uncertainty
        flags set. This ensures the comparison pipeline returns 'inconclusive'
        rather than hallucinating deviations from non-existent data.
        """
        from datetime import datetime
        from schemas.ir import UncertaintyFlag

        contract = ScientificContract(
            doc_id=doc_id,
            doc_type=doc_type,
            title=f"{category.replace('_', ' ').title()}: {Path(parsed.source_path).stem}",
            authors=[],
            hypotheses=[],
            outcomes=[],
            analyses=[],
            claims=[],
            exclusion_criteria=[],
            sample_size=None,
            domain_params=DomainSpecificParameters(),
            raw_markdown=parsed.markdown,
            extraction_confidence=0.0,
            overall_uncertainty=UncertaintyFlag(
                is_uncertain=True,
                reason=(
                    f"Document classified as '{category}', not a clinical trial. "
                    "No hypotheses, outcomes, sample sizes, or analyses to extract. "
                    "Comparison results should be treated as INCONCLUSIVE."
                ),
                missing_data=[
                    "clinical trial hypotheses",
                    "primary/secondary outcomes",
                    "sample size justification",
                    "statistical analysis plan"
                ],
                resolution_suggestion=(
                    "This document is not suitable for clinical trial registration "
                    "comparison. Use protocol-to-protocol or guidance-to-guidance "
                    "comparison modes instead."
                ),
            ),
            compilation_timestamp=datetime.now(),
        )

        logger.info(
            f"Created non-trial contract for {doc_id}: {category}, "
            f"all scientific fields empty, uncertainty flagged"
        )
        return contract


def create_mock_contract(doc_id: str, doc_type: str) -> ScientificContract:
    """Create a mock ScientificContract for testing without LLM calls."""
    from datetime import datetime

    return ScientificContract(
        doc_id=doc_id,
        doc_type=doc_type,
        title=f"Mock {doc_type.title()} Document",
        authors=["Author A", "Author B"],
        hypotheses=[
            Hypothesis(
                id="H1",
                description="Cognitive behavioral therapy will reduce anxiety scores by at least 20%",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=["anxiety_score", "CBT"],
                direction="greater",
            ),
            Hypothesis(
                id="H2",
                description="CBT effects will persist at 6-month follow-up",
                hypothesis_type=HypothesisType.SECONDARY,
                variables=["anxiety_score", "follow_up"],
            ),
        ],
        outcomes=[
            Outcome(
                id="O1",
                measure="GAD-7 Anxiety Scale",
                timepoint="post-intervention",
                outcome_type=OutcomeType.PRIMARY,
            ),
            Outcome(
                id="O2",
                measure="PHQ-9 Depression Scale",
                timepoint="post-intervention",
                outcome_type=OutcomeType.SECONDARY,
            ),
        ],
        sample_size=SampleSize(
            planned_n=200,
            power_analysis="Power=0.80, alpha=0.05, d=0.5",
        ),
        exclusion_criteria=[
            ExclusionCriterion(
                id="E1",
                description="Current suicidal ideation",
                criterion_type="exclusion",
            ),
        ],
        analyses=[
            StatisticalAnalysis(
                id="SA1",
                model="ANCOVA",
                dependent_variable="GAD-7 post",
                covariates=["GAD-7 baseline", "age", "gender"],
            ),
        ],
        claims=[],
        domain_params=DomainSpecificParameters(),
        compilation_timestamp=datetime.now(),
    )


def ctgov_json_to_contract(json_data: dict, doc_type: str = "registration") -> ScientificContract:
    """Convert ClinicalTrials.gov JSON directly to ScientificContract — no LLM.

    This is the architecturally correct path for CT.gov data:
        CT.gov JSON → ScientificContract

    Instead of:
        CT.gov JSON → markdown → LLM extraction → ScientificContract

    The JSON already contains structured outcomes, eligibility, enrollment, and arms.
    Extracting them deterministically eliminates LLM hallucination on the registration side.

    This means the registration ScientificContract is always accurate,
    and the LLM is only used for the publication (unstructured PDF).
    """
    from datetime import datetime
    import re as _re

    proto = json_data.get("protocolSection", {})
    ident = proto.get("identificationModule", {})
    design = proto.get("designModule", {})
    outcomes = proto.get("outcomesModule", {})
    eligibility = proto.get("eligibilityModule", {})
    arms = proto.get("armsInterventionsModule", {})
    status = proto.get("statusModule", {})
    description = proto.get("descriptionModule", {})

    nct_id = ident.get("nctId", "")
    title = ident.get("officialTitle") or ident.get("briefTitle", "")

    # ── Outcomes ──
    extracted_outcomes = []
    outcome_idx = 0

    for o in outcomes.get("primaryOutcomes", []):
        outcome_idx += 1
        measure = o.get("measure", "")
        timepoint = o.get("timeFrame", "")
        desc = o.get("description", "")
        extracted_outcomes.append(Outcome(
            id=f"O{outcome_idx}",
            measure=measure,
            timepoint=timepoint or None,
            outcome_type=OutcomeType.PRIMARY,
            description=desc or None,
            evidence=[EvidenceSpan(
                text=f"{measure}" + (f" ({timepoint})" if timepoint else ""),
                source_doc="registration",
                section="Primary Outcomes",
            )],
            status=FieldStatus.PRESENT,
        ))

    for o in outcomes.get("secondaryOutcomes", []):
        outcome_idx += 1
        measure = o.get("measure", "")
        timepoint = o.get("timeFrame", "")
        desc = o.get("description", "")
        extracted_outcomes.append(Outcome(
            id=f"O{outcome_idx}",
            measure=measure,
            timepoint=timepoint or None,
            outcome_type=OutcomeType.SECONDARY,
            description=desc or None,
            evidence=[EvidenceSpan(
                text=f"{measure}" + (f" ({timepoint})" if timepoint else ""),
                source_doc="registration",
                section="Secondary Outcomes",
            )],
            status=FieldStatus.PRESENT,
        ))

    # ── Sample Size ──
    enroll = design.get("enrollmentInfo", {})
    sample_size = None
    if enroll.get("count"):
        sample_size = SampleSize(
            planned_n=enroll["count"],
            evidence=[EvidenceSpan(
                text=f"Enrollment: {enroll['count']}",
                source_doc="registration",
                section="Enrollment",
            )],
            status=FieldStatus.PRESENT,
        )

    # ── Eligibility Criteria ──
    criteria_text = eligibility.get("eligibilityCriteria", "")
    exclusion_criteria = []
    if criteria_text:
        # Split into inclusion/exclusion sections
        in_section = False
        ex_section = False
        current_items = []

        for line in criteria_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            lower = line.lower()
            if "inclusion criteria" in lower:
                in_section = True
                ex_section = False
                continue
            if "exclusion criteria" in lower:
                in_section = False
                ex_section = True
                continue
            if line.startswith("*") or line.startswith("-"):
                item = line.lstrip("*- ").strip()
                if item:
                    criterion_type = "inclusion" if in_section else ("exclusion" if ex_section else "exclusion")
                    idx = len(exclusion_criteria) + 1
                    exclusion_criteria.append(ExclusionCriterion(
                        id=f"EC{idx}",
                        description=item[:500],
                        criterion_type=criterion_type,
                        evidence=[EvidenceSpan(
                            text=item[:300],
                            source_doc="registration",
                            section="Eligibility Criteria",
                        )],
                    ))

    # ── Hypotheses (from primary outcomes — CT.gov doesn't have explicit hypotheses) ──
    hypotheses = []
    for i, o in enumerate(extracted_outcomes):
        if o.outcome_type == OutcomeType.PRIMARY:
            hypotheses.append(Hypothesis(
                id=f"H{i+1}",
                description=f"The intervention will show a statistically significant effect on: {o.measure}",
                hypothesis_type=HypothesisType.PRIMARY,
                variables=[o.measure],
                direction="two-sided",
                evidence=o.evidence,
                status=FieldStatus.PRESENT,
            ))

    # ── Build markdown from structured data ──
    md_parts = [f"# Study Registration: {nct_id}", ""]
    md_parts.append(f"## Title\n{title}")
    md_parts.append(f"\n## Status: {status.get('overallStatus', 'Unknown')}")
    md_parts.append(f"Study Type: {design.get('studyType', 'Unknown')}")
    md_parts.append(f"Phase: {', '.join(design.get('phases', ['N/A']))}")
    if enroll.get("count"):
        md_parts.append(f"\n## Planned Enrollment: {enroll['count']}")
    if outcomes.get("primaryOutcomes"):
        md_parts.append("\n## Primary Outcomes")
        for i, o in enumerate(outcomes["primaryOutcomes"], 1):
            md_parts.append(f"{i}. **{o.get('measure', '?')}**")
            if o.get("timeFrame"):
                md_parts.append(f"   Time Frame: {o['timeFrame']}")
    if outcomes.get("secondaryOutcomes"):
        md_parts.append("\n## Secondary Outcomes")
        for i, o in enumerate(outcomes["secondaryOutcomes"], 1):
            md_parts.append(f"{i}. **{o.get('measure', '?')}**")
    if criteria_text:
        md_parts.append(f"\n## Eligibility Criteria\n{criteria_text[:3000]}")
    raw_markdown = "\n".join(md_parts)

    return ScientificContract(
        doc_id=nct_id or f"{doc_type}_ctgov",
        doc_type=doc_type,
        title=title,
        registration_id=nct_id,
        hypotheses=hypotheses,
        outcomes=extracted_outcomes,
        sample_size=sample_size,
        exclusion_criteria=exclusion_criteria,
        analyses=[],
        claims=[],
        domain_params=DomainSpecificParameters(),
        raw_markdown=raw_markdown,
        extraction_confidence=1.0,
        overall_uncertainty=UncertaintyFlag(is_uncertain=False),
        compilation_timestamp=datetime.now(),
    )
