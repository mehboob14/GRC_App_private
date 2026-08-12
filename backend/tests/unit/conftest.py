"""Unit tests read no file and reach no service.

Several of these construct :class:`~verity.core.config.Settings` directly. pydantic-settings
would otherwise load a developer's repository-root ``.env``, so the same assertion would pass
on one machine and fail on another depending on what happens to be in it. Environment
variables still apply — ``pytest_configure`` in the parent conftest sets a known set — but
the files do not.
"""

from __future__ import annotations

import pytest
from pydantic_settings import BaseSettings

from verity.core.config import Settings


def _settings_classes() -> list[type[BaseSettings]]:
    """Settings and every grouped section nested under it."""
    sections = [
        field.annotation
        for field in Settings.model_fields.values()
        if isinstance(field.annotation, type) and issubclass(field.annotation, BaseSettings)
    ]
    return [Settings, *sections]


@pytest.fixture(autouse=True)
def _ignore_dotenv_files(monkeypatch: pytest.MonkeyPatch) -> None:
    for settings_class in _settings_classes():
        monkeypatch.setitem(settings_class.model_config, "env_file", None)
