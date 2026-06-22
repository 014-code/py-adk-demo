"""Model and runtime configuration for the ADK agent package."""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm

DEFAULT_MODEL_NAME = "openai/doubao-seed-2-0-mini-260215"


def build_model() -> LiteLlm:
    """Create the model object shared by all agents in this package.

    ADK accepts either a native model string or a model object. This project uses
    LiteLLM so the same Agent code can talk to an OpenAI-compatible endpoint
    such as Volcano Engine ARK.
    """
    return LiteLlm(
        model=os.getenv("ADK_MODEL", DEFAULT_MODEL_NAME),
        # Doubao reasoning models may emit a long thought trace by default.
        # The ARK OpenAI-compatible API accepts this provider-specific option.
        extra_body={"thinking": {"type": "disabled"}},
    )


MODEL = build_model()