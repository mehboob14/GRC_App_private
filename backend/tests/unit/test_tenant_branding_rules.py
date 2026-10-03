"""Branding's pure rules: what a logo may be and what branding may store.

No database. The routes that use these are proven end to end in
``tests/integration/test_tenant_branding.py``; this file pins the decisions
themselves so a loosened pattern or an extra accepted type fails fast.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from verity.modules.tenancy.schemas import BrandingPut, TenantUpdate
from verity.modules.tenancy.service import LOGO_MAX_BYTES, _logo_content_type

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
WEBP = b"RIFF\x1a\x00\x00\x00WEBPVP8 " + b"\x00" * 16


def test_a_logo_is_a_png_a_jpeg_or_a_webp_read_from_the_bytes() -> None:
    assert _logo_content_type(PNG) == "image/png"
    assert _logo_content_type(JPEG) == "image/jpeg"
    assert _logo_content_type(WEBP) == "image/webp"


@pytest.mark.parametrize(
    "data",
    [
        b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>',
        b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"/>',
        b"  <svg/>",
        b"GIF89a" + b"\x00" * 16,
        b"%PDF-1.7\n",
        b"<!doctype html><html></html>",
        b"just some text",
        b'{"logo": true}',
        b"PK\x03\x04word/document.xml",
        b"",
    ],
    ids=["svg", "svg-xml", "svg-padded", "gif", "pdf", "html", "text", "json", "docx", "empty"],
)
def test_anything_else_is_not_a_logo(data: bytes) -> None:
    """SVG above all: it is markup a browser can run script from."""
    assert _logo_content_type(data) is None


def test_the_logo_limit_is_512_kb() -> None:
    assert LOGO_MAX_BYTES == 512 * 1024


@pytest.mark.parametrize("colour", ["#0f172a", "#0F172A", "#000000", "#ffffff"])
def test_branding_stores_six_digit_hex_colours(colour: str) -> None:
    body = BrandingPut(primary_color=colour, secondary_color=colour)
    assert body.primary_color == colour


@pytest.mark.parametrize(
    "colour",
    [
        "red",
        "#123",
        "#12345",
        "#1234567",
        "#12345g",
        "0f172a",
        "rgb(1, 2, 3)",
        "#0f172a;}body{display:none",
        "url(javascript:alert(1))",
        "",
    ],
)
def test_branding_refuses_anything_that_is_not_a_hex_colour(colour: str) -> None:
    """The value ends up in a stylesheet in every member's browser."""
    for field in ("primary_color", "secondary_color"):
        with pytest.raises(ValidationError):
            BrandingPut(**{field: colour})


def test_branding_bounds_its_free_text() -> None:
    with pytest.raises(ValidationError):
        BrandingPut(document_footer="x" * 1001)
    with pytest.raises(ValidationError):
        BrandingPut(email_from_name="x" * 201)
    with pytest.raises(ValidationError):
        BrandingPut(email_from_address="x" * 321)
    assert BrandingPut(document_footer="x" * 1000).document_footer == "x" * 1000


def test_an_omitted_credential_is_distinguishable_from_a_cleared_one() -> None:
    """The service keeps the stored credential when the field was never sent."""
    assert "smtp_config_ref" not in BrandingPut(primary_color="#111111").model_fields_set
    assert "smtp_config_ref" in BrandingPut(smtp_config_ref=None).model_fields_set
    assert "smtp_config_ref" in BrandingPut(smtp_config_ref="smtp://x").model_fields_set


def test_a_profile_update_cannot_clear_the_two_required_columns() -> None:
    """An explicit null would try to NULL a NOT NULL column and answer 500."""
    for field in ("legal_name", "plan"):
        with pytest.raises(ValidationError):
            TenantUpdate(**{field: None})
    assert TenantUpdate(city=None).model_fields_set == {"city"}
    assert TenantUpdate(plan="growth").plan == "growth"
