"""IAM invariants provable without a database: the untouched federation seam,
the built-in role table, the password policy, and slug derivation."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from verity.modules.iam.exceptions import WeakPassword
from verity.modules.iam.service import (
    BUILT_IN_ROLE_DESCRIPTIONS,
    BUILT_IN_ROLE_KEYS,
    MIN_PASSWORD_LENGTH,
    PasswordPolicy,
    derive_slug_candidates,
    normalize_email,
    tenant_display_name,
    validate_password,
)
from verity.modules.tenancy.schemas import SLUG_PATTERN

_IAM_DIR = Path(__file__).resolve().parents[2] / "src" / "verity" / "modules" / "iam"


def _executable_surface(source: str) -> str:
    """The module's code with comments and docstrings removed.

    Documentation may *name* the seam — a docstring explaining why the table is
    absent is exactly what should exist — but no import, identifier, or SQL
    string may reach it. Parsing drops comments; blanking the docstring nodes
    drops the prose; ``ast.unparse`` gives back only what executes.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = node.body
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            body[0].value = ast.Constant(value="")
    return ast.unparse(tree)


@pytest.mark.parametrize("filename", ["router.py", "service.py", "schemas.py", "sso.py"])
def test_the_federation_seam_is_reached_only_through_its_repository(filename: str) -> None:
    """ADR-0015: SSO sign in uses ``user_identities`` now (ADR-0006 kept it unused until then).
    Only ``IdentityRepository`` in repository.py reads or writes it; everything else goes through
    that repository."""
    source = (_IAM_DIR / filename).read_text(encoding="utf-8")
    code = _executable_surface(source)
    assert "UserIdentity" not in code, f"{filename} imports the federation seam"
    assert "user_identities" not in code, f"{filename} references the seam's table"


def test_the_built_in_roles_are_exactly_the_designed_set() -> None:
    assert list(BUILT_IN_ROLE_KEYS) == [
        "Admin",
        "Chief Executive Officer",
        "Security Officer",
        "Privacy Officer",
        "Engineering Lead",
        "Business Operations/Finance Lead",
        "Compliance Manager",
    ]
    # Admin is "every key that exists", resolved at check time — no static list.
    assert BUILT_IN_ROLE_KEYS["Admin"] is None
    # The appointments start read-only; an admin widens them in the UI.
    for name, keys in BUILT_IN_ROLE_KEYS.items():
        if name in {"Admin", "Compliance Manager"}:
            continue
        assert keys is not None
        assert all(key.endswith(":read") for key in keys), name


def test_the_compliance_manager_runs_the_programme_but_never_administers_the_workspace() -> None:
    """Guided onboarding D-12. Inviting can hand out Admin, ``tenant:manage`` sets the mail
    server, and approvals belong to management: none of them is in this role."""
    keys = set(BUILT_IN_ROLE_KEYS["Compliance Manager"] or ())
    assert {"controls:manage", "evidence:manage", "documents:manage", "risks:manage"} <= keys
    never = {
        "members:invite",
        "members:manage",
        "members:disable",
        "roles:manage",
        "groups:manage",
        "security:manage",
        "tenant:manage",
        "documents:approve",
        "risks:approve",
        "vendors:approve",
        "tasks:approve",
        "vulnerabilities:accept",
    }
    assert not keys & never


def test_every_built_in_role_ships_a_description() -> None:
    """A role list where half the rows explain themselves and half do not is
    worse than one that never promised. The two tables move together."""
    assert set(BUILT_IN_ROLE_DESCRIPTIONS) == set(BUILT_IN_ROLE_KEYS)
    assert all(text.strip() for text in BUILT_IN_ROLE_DESCRIPTIONS.values())


def test_password_policy_floor_and_default_rules() -> None:
    # A workspace may loosen its policy down to the platform floor, never below it.
    loosest = PasswordPolicy(
        min_length=1,
        require_upper=False,
        require_lower=False,
        require_digit=False,
        require_symbol=False,
    )
    with pytest.raises(WeakPassword):
        validate_password("a" * (MIN_PASSWORD_LENGTH - 1), loosest)
    validate_password("a" * MIN_PASSWORD_LENGTH, loosest)
    # The default asks for 12 characters with an upper, a lower, a digit and a symbol.
    with pytest.raises(WeakPassword):
        validate_password("a" * MIN_PASSWORD_LENGTH)
    validate_password("Harbor!light9")


def test_slug_candidates_are_deterministic_and_dns_safe() -> None:
    first = derive_slug_candidates("Acme GmbH & Co. KG", "founder@acme.example")
    second = derive_slug_candidates("Acme GmbH & Co. KG", "founder@acme.example")
    assert first == second, "an idempotent retry must derive the same slugs"
    base, fallback = first
    assert base == "acme-gmbh-co-kg"
    assert fallback.startswith(base + "-")
    for slug in (base, fallback):
        assert re.match(SLUG_PATTERN, slug), slug
        assert len(slug) <= 63


def test_slug_falls_back_to_a_placeholder_for_unusable_names() -> None:
    base, fallback = derive_slug_candidates("!!!", "x@example.com")
    assert base == "workspace"
    assert re.match(SLUG_PATTERN, fallback)


def test_email_normalisation_and_display_name() -> None:
    assert normalize_email("  Founder@Acme.example ") == "founder@acme.example"
    assert tenant_display_name("Acme GmbH", None) == "Acme GmbH"
    assert tenant_display_name("Acme GmbH", "Acme") == "Acme"
