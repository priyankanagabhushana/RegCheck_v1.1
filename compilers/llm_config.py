"""LLM Configuration — supports DeepSeek, OpenAI, Claude, Gemini via LiteLLM.

All LLM calls go through this module. API keys are stored in Streamlit session state
and configured via the Settings page.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from pydantic import ValidationError

logger = logging.getLogger(__name__)

PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "models": [
            "deepseek/deepseek-chat",
            "deepseek/deepseek-coder",
            "deepseek/deepseek-reasoner",
        ],
        "default_model": "deepseek/deepseek-chat",
        "env_key": "DEEPSEEK_API_KEY",
    },
    "openai": {
        "name": "OpenAI",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-mini"],
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
    "anthropic": {
        "name": "Anthropic (Claude)",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "default_model": "claude-sonnet-4-20250514",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "gemini": {
        "name": "Google (Gemini)",
        "models": ["gemini/gemini-2.0-flash", "gemini/gemini-1.5-pro", "gemini/gemini-1.5-flash"],
        "default_model": "gemini/gemini-2.0-flash",
        "env_key": "GEMINI_API_KEY",
    },
}


def get_active_config(session_state: dict) -> dict:
    """Get the active LLM configuration from session state."""
    provider = session_state.get("llm_provider", "deepseek")
    if provider not in PROVIDERS:
        provider = "deepseek"

    provider_config = PROVIDERS[provider]
    api_key = session_state.get(f"api_key_{provider}", "")
    model = session_state.get("llm_model") or provider_config["default_model"]
    if model not in provider_config["models"]:
        model = provider_config["default_model"]

    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
    }


def call_llm(
    messages: list[dict],
    model: str,
    api_key: str,
    response_format: Optional[dict] = None,
    temperature: float = 0.1,
) -> str:
    """Call an LLM via LiteLLM with the given configuration.

    Supports DeepSeek, OpenAI, Claude, Gemini through a unified interface.
    """
    import litellm

    # Set the API key based on provider
    if model.startswith("deepseek/"):
        import os
        os.environ["DEEPSEEK_API_KEY"] = api_key
    elif model.startswith("claude"):
        import os
        os.environ["ANTHROPIC_API_KEY"] = api_key
    elif model.startswith("gemini/"):
        import os
        os.environ["GEMINI_API_KEY"] = api_key
    else:
        import os
        os.environ["OPENAI_API_KEY"] = api_key

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }

    if response_format:
        kwargs["response_format"] = response_format

    response = litellm.completion(**kwargs)
    return response.choices[0].message.content


def call_llm_structured(
    messages: list[dict],
    model: str,
    api_key: str,
    schema: type,
    temperature: float = 0.1,
) -> dict:
    """Call LLM and parse response into a Pydantic model.

    Uses JSON mode + Pydantic validation with self-correction on failure.
    """
    from schemas.ir import ScientificContract

    # First attempt: ask for JSON
    json_messages = messages + [
        {"role": "system", "content": "Return ONLY a valid JSON object. No markdown, no explanation, no code fences."}
    ]

    for attempt in range(3):
        try:
            raw = call_llm(
                json_messages,
                model=model,
                api_key=api_key,
                response_format={"type": "json_object"},
                temperature=temperature,
            )

            # Clean the response
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r'^```\w*\n?', '', raw)
                raw = re.sub(r'\n?```$', '', raw)

            data = json.loads(raw)
            validated = schema.model_validate(data)
            return validated.model_dump()

        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                json_messages.append({
                    "role": "user",
                    "content": f"Your previous response had an error: {e}\nPlease fix it and return a valid JSON object."
                })

    raise ValueError(f"Failed to get valid JSON from LLM after 3 attempts")
