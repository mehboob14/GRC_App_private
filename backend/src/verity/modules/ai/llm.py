"""The LangChain chat client, traced to LangSmith.

Guardrail
---------
Every call made through this client produces a **draft**. Rule 8: AI never publishes and
never decides. A caller takes the returned text, records it with ``origin = ai_draft``,
and puts it in front of a person through the same approval gate human content goes
through. A caller that writes an AI response straight into a published document, a
control status, a finding resolution, or a risk score is a defect regardless of what the
tests say — it removes the human review that is the reason an auditor can trust this
product at all.

Tracing exists for the same reason. docs/architecture/ai-features.md requires prompts
and outputs to be logged with the tenant, actor, model, and version, so a bad draft is
traceable to what produced it. A client that is not traced cannot satisfy that, which is
why tracing is wired now, before there is a single feature to trace.

Availability
------------
An LLM provider is a third party and is not reliable. Calls carry a timeout and a
bounded retry. Phase 2 adds the circuit breaker and the degrade-to-manual fallback that
docs/architecture/ai-features.md requires — a provider outage must never stop someone
writing their own policy.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from verity.core.config import Settings, get_settings
from verity.core.logging import get_logger

logger = get_logger(__name__)


def configure_tracing(settings: Settings) -> bool:
    """Export the LangSmith settings into the process environment.

    The LangSmith and LangChain SDKs read their configuration from ambient environment
    variables, and there is no supported way to hand them a settings object. So
    ``core.config`` stays the single source of truth and this function pushes it
    outwards, rather than having two places that can disagree about whether tracing is
    on.

    Returns:
        Whether tracing was enabled.
    """
    langsmith = settings.langsmith
    if not langsmith.tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        return False
    if langsmith.api_key is None:
        # Enabling tracing without a key makes every call emit a failed export
        # alongside the real request. Better to run untraced and say so.
        logger.warning("ai.tracing_disabled", reason="LANGSMITH_API_KEY is not set")
        os.environ["LANGSMITH_TRACING"] = "false"
        return False

    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = langsmith.api_key.get_secret_value()
    os.environ["LANGSMITH_PROJECT"] = langsmith.project
    os.environ["LANGSMITH_ENDPOINT"] = langsmith.endpoint
    logger.info("ai.tracing_enabled", project=langsmith.project, endpoint=langsmith.endpoint)
    return True


def build_chat_model(settings: Settings) -> BaseChatModel:
    """Construct a chat model from settings.

    Provider-agnostic on purpose: ``init_chat_model`` resolves the provider at call
    time, so changing model or vendor is configuration rather than a code change in
    every prompt site.
    """
    configure_tracing(settings)
    ai = settings.ai
    # Reasoning models (gpt-5, o-series) refuse a temperature and fix their own sampling.
    reasoning = ai.model.startswith(("gpt-5", "o1", "o3", "o4"))
    options: dict[str, Any] = {} if reasoning else {"temperature": ai.temperature}
    model: BaseChatModel = init_chat_model(
        model=ai.model,
        model_provider=ai.provider,
        **options,
        max_tokens=ai.max_tokens,
        timeout=ai.timeout_seconds,
        max_retries=ai.max_retries,
        api_key=ai.api_key.get_secret_value() if ai.api_key else None,
    )
    logger.info("ai.client_ready", provider=ai.provider, model=ai.model)
    return model


@lru_cache(maxsize=1)
def get_chat_model() -> BaseChatModel:
    """The process-wide chat model, constructed on first use."""
    return build_chat_model(get_settings())


def reset_chat_model_cache() -> None:
    """Discard the cached model. For tests that vary provider settings."""
    get_chat_model.cache_clear()
