"""Contract Extractor - Compiles parsed documents into ScientificContract IR.

Uses LLM structured output (via instructor or native Pydantic validation)
with a self-correction loop on validation errors.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from parsers.base import ParsedDocument
from schemas.ir import (
    DomainSpecificParameters,
    EvidenceSpan,
    ExclusionCriterion,
    Hypothesis,
    HypothesisType,
    Outcome,
    OutcomeType,
    SampleSize,
    ScientificClaim,
    ScientificContract,
    ScientificAnalysis as StatisticalAnalysis,
)

logger = logging.getLogger(__name__)


EXTRACTION_SYSTEM_PROMPT = """You are a scientific document analyst. Your task is to extract structured information from a scientific document (either a study registration/pre-registration or a published paper) into a precise JSON format.

Rules:
1. Extract ONLY information explicitly stated in the document.
2. If information is not present, use null or empty list.
3. Assign sequential IDs (H1, H2, O1, O2, SA1, SA2, C1, C2, etc.)
4. For each extracted object, include the exact supporting text as evidence spans.
5. Be precise about hypothesis types (primary/secondary/exploratory) and outcome types.
6. For statistical analyses, capture the full model specification.
7. Do NOT infer or hallucinate information not in the source text.

Output a JSON object matching the ScientificContract schema."""

EXTRACTION_USER_PROMPT = """Extract the structured scientific information from this document.

Document type: {doc_type}
Document ID: {doc_id}

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
- hypotheses: list of {{id, description, hypothesis_type, variables, direction, evidence: [{{text, source_doc}}]}}
- outcomes: list of {{id, measure, timepoint, outcome_type, description, evidence: [{{text, source_doc}}]}}
- sample_size: {{planned_n, actual_n, power_analysis, dropout_rate, justification, evidence: [{{text, source_doc}}]}}
- exclusion_criteria: list of {{id, description, criterion_type, evidence: [{{text, source_doc}}]}}
- analyses: list of {{id, model, dependent_variable, independent_variables, covariates, corrections, software, evidence: [{{text, source_doc}}]}}
- claims: list of {{id, text, mapped_hypothesis_id, strength, supporting_evidence: [{{text, source_doc}}]}}

Return ONLY the JSON object, no other text."""


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

        Args:
            parsed: The parsed document output
            doc_type: Either 'registration' or 'publication'

        Returns:
            Validated ScientificContract
        """
        doc_id = f"{doc_type}_{Path(parsed.source_path).stem}"

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

        user_prompt = EXTRACTION_USER_PROMPT.format(
            doc_type=doc_type,
            doc_id=doc_id,
            markdown=markdown_content,
            tables_section=tables_section,
        )

        return self._extract_with_retry(user_prompt, doc_id, doc_type, parsed.markdown)

    def _extract_with_retry(
        self, prompt: str, doc_id: str, doc_type: str, raw_markdown: str
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
                logger.info(
                    f"Successfully extracted contract for {doc_id}: "
                    f"{contract.summary_stats()}"
                )
                return contract

            except ValidationError as e:
                last_error = e
                logger.warning(
                    f"Validation error on attempt {attempt + 1}/{self.max_retries}: {e}"
                )
                # Feed error back to LLM
                prompt = (
                    f"{prompt}\n\n"
                    f"PREVIOUS ATTEMPT FAILED with validation error:\n{e}\n\n"
                    f"Fix the schema violations and return a valid JSON object."
                )

        raise ValueError(
            f"Failed to extract valid ScientificContract after {self.max_retries} attempts. "
            f"Last error: {last_error}"
        )

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
