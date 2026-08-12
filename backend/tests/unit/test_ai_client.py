"""The LangSmith-traced client constructs, and tracing is driven from settings only."""

from __future__ import annotations

import os

import pytest
from pydantic import SecretStr

from verity.core.config import AISettings, LangSmithSettings, Settings
from verity.modules.ai.llm import build_chat_model, configure_tracing

TRACING_VARS = (
    "LANGSMITH_TRACING",
    "LANGSMITH_API_KEY",
    "LANGSMITH_PROJECT",
    "LANGSMITH_ENDPOINT",
)


@pytest.fixture(autouse=True)
def _clear_tracing_environment() -> None:
    for name in TRACING_VARS:
        os.environ.pop(name, None)


def _settings(langsmith: LangSmithSettings, ai: AISettings | None = None) -> Settings:
    return Settings(
        env="test",
        langsmith=langsmith,
        ai=ai or AISettings(api_key=SecretStr("test-key-not-used-offline")),
    )


def test_tracing_is_enabled_from_settings() -> None:
    enabled = configure_tracing(
        _settings(
            LangSmithSettings(
                tracing=True,
                api_key=SecretStr("ls-test-key"),
                project="verity-test",
            )
        )
    )
    assert enabled
    assert os.environ["LANGSMITH_TRACING"] == "true"
    assert os.environ["LANGSMITH_PROJECT"] == "verity-test"
    assert os.environ["LANGSMITH_ENDPOINT"]


def test_tracing_off_by_default() -> None:
    assert not configure_tracing(_settings(LangSmithSettings()))
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_tracing_without_a_key_degrades_rather_than_failing_every_call() -> None:
    """Enabled-but-keyless would make every call emit a failed export beside the request."""
    assert not configure_tracing(_settings(LangSmithSettings(tracing=True)))
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_client_constructs_with_tracing_enabled() -> None:
    """Construction only. No request leaves the process, so no network and no key needed."""
    model = build_chat_model(
        _settings(
            LangSmithSettings(tracing=True, api_key=SecretStr("ls-test-key")),
            AISettings(
                provider="openai",
                model="gpt-4o-mini",
                api_key=SecretStr("sk-test-not-a-real-key"),
                timeout_seconds=12.5,
                max_retries=1,
            ),
        )
    )
    assert model is not None
    assert os.environ["LANGSMITH_TRACING"] == "true"


def test_client_carries_the_configured_timeout_and_retry_budget() -> None:
    """An LLM provider is a third party: every call is bounded (ai-features.md)."""
    ai = AISettings(
        api_key=SecretStr("sk-test-not-a-real-key"),
        timeout_seconds=7.0,
        max_retries=3,
    )
    model = build_chat_model(_settings(LangSmithSettings(), ai))
    assert getattr(model, "request_timeout", None) == 7.0
    assert getattr(model, "max_retries", None) == 3
