"""The access log must never carry a portal token.

The vendor portal puts its credential in the URL path, and this application logs
``scope["path"]`` on every request plus once more in each exception handler. That
made the access log the one place the live token was written in the clear, for the
thirty days the link stays valid — found by the section-3 security review.

``safe_path`` is the fix, and these tests exist because the failure is silent: the
logs simply contain a token, nothing breaks, and nobody notices until somebody
reads them.
"""

from __future__ import annotations

import pytest

from verity.core.middleware import safe_path

TOKEN = "kQ3vN8pR2xL7mY4wT6bH1sD9fG5jK0zC8vB3nM6qA2e"  # noqa: S105 — the thing under test


def test_a_portal_token_never_survives_into_a_log_line() -> None:
    assert TOKEN not in safe_path(f"/api/v1/vendor-portal/{TOKEN}")


@pytest.mark.parametrize(
    "suffix",
    ["", "/answers", "/submit", f"/answers/{'0' * 8}-0000-0000-0000-{'0' * 12}/evidence"],
)
def test_every_portal_route_shape_is_redacted(suffix: str) -> None:
    """The token is the first segment after the prefix on all four routes, so all
    four must lose it — including the ones with more path after it."""
    redacted = safe_path(f"/api/v1/vendor-portal/{TOKEN}{suffix}")
    assert TOKEN not in redacted
    assert redacted == f"/api/v1/vendor-portal/[redacted]{suffix}"


def test_the_rest_of_the_line_survives() -> None:
    """A log entry that loses the route is a log entry nobody can use. Only the
    credential goes."""
    assert safe_path(f"/api/v1/vendor-portal/{TOKEN}/submit").endswith("/submit")


def test_a_path_with_no_credential_is_returned_unchanged() -> None:
    for path in ("/api/v1/vendors", "/api/v1/vendors/123/findings", "/healthz", "/"):
        assert safe_path(path) == path


def test_a_missing_path_is_an_empty_string_not_a_crash() -> None:
    """This runs in a ``finally`` block on every request, including the ones that
    already failed. Raising here would replace a real error with this one."""
    assert safe_path(None) == ""
    assert safe_path("") == ""


def test_a_bare_prefix_with_no_token_is_harmless() -> None:
    assert safe_path("/api/v1/vendor-portal/") == "/api/v1/vendor-portal/[redacted]"


def test_the_marker_is_matched_anywhere_the_router_could_be_mounted() -> None:
    """The prefix is applied at mount time in main.py, so the check must not
    assume the current one — moving the mount must not silently unredact."""
    assert TOKEN not in safe_path(f"/vendor-portal/{TOKEN}")
    assert TOKEN not in safe_path(f"/api/v2/vendor-portal/{TOKEN}")
