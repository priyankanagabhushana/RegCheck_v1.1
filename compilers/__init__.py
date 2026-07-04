"""Contract Compiler - Extract ScientificContract from parsed documents.

Uses LLM structured output with Pydantic validation self-correction loop.
"""

from .contract_extractor import ContractExtractor

__all__ = ["ContractExtractor"]
