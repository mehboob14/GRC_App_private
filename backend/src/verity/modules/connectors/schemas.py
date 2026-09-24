"""Wire shapes for connections, runs, the control Automation panel and requests.

The token arrives as ``SecretStr`` so it is masked in every repr, validation error
and log line the request could reach (rule 6). Nothing here ever sends it back.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConnectWrite(_Request):
    provider: Literal["github"]
    token: SecretStr = Field(min_length=1, max_length=400)
    account: str | None = Field(default=None, max_length=100)


class DisconnectWrite(_Request):
    reason: str = Field(min_length=1, max_length=500)


class IntegrationRequestWrite(_Request):
    provider_name: str = Field(min_length=1, max_length=120)
    capability_key: str | None = Field(default=None, max_length=60)
    control_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


class RunOut(_Response):
    id: uuid.UUID
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    resources: int
    passed: int
    failed: int
    errored: int
    error: str | None
    evidence_id: uuid.UUID | None


class ConnectionOut(_Response):
    id: uuid.UUID
    provider: str
    provider_name: str
    account_login: str
    account_type: str
    display_name: str
    status: str
    credential_hint: str | None
    credential_expires_at: datetime | None
    last_run_at: datetime | None
    last_success_at: datetime | None
    last_error: str | None
    error_streak: int
    created_at: datetime
    disconnected_at: datetime | None
    latest_run: RunOut | None


class ProviderOut(_Response):
    key: str
    name: str
    status: str
    phase: str | None
    capabilities: list[str]


class ProviderOptionOut(_Response):
    key: str
    name: str
    status: str
    phase: str | None
    connected: bool
    runs_check: bool


class CapabilityOut(_Response):
    key: str
    name: str
    description: str
    providers: list[ProviderOptionOut]


class ResultOut(_Response):
    connection_id: uuid.UUID
    account: str
    resource_type: str
    resource_name: str
    outcome: str
    summary: str
    url: str | None
    detail: dict[str, Any]
    observed_at: datetime


class TestOut(_Response):
    key: str
    name: str
    description: str
    remediation: str
    frequency: str
    coverage: str
    capabilities: list[str]
    status: str
    results: list[ResultOut]
    counts: dict[str, int]
    last_run_at: datetime | None


class DayOut(_Response):
    day: date
    status: str


class IntegrationRequestOut(_Response):
    id: uuid.UUID
    provider_name: str
    capability_key: str | None
    control_id: uuid.UUID | None
    note: str | None
    status: str
    created_at: datetime


class AutomationOut(_Response):
    control_id: uuid.UUID
    mode: str
    status: str
    tests_total: int
    tests_running: int
    last_run_at: datetime | None
    running: bool
    connection_ids: list[uuid.UUID]
    capabilities: list[CapabilityOut]
    tests: list[TestOut]
    history: list[DayOut]
    requests: list[IntegrationRequestOut]
