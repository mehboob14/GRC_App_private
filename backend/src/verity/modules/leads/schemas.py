"""Request and response models for the public demo-request form.

The request is the contract with the website and is fixed: snake_case keys, the limits
below, unknown keys refused like every other request in this API. The answer to a request
is ``{"status": "received"}`` whatever became of it, including a honeypot hit.

Every free-text field is normalised on the way in (:func:`clean_line`,
:func:`clean_text`) before its length is judged: control characters never reach the
database, where a NUL byte is a driver error that would put the visitor's details into an
exception message, and never reach a mail header or a plain-text body, where a newline is
a way to forge a line. Messages here are fixed strings and never echo the value, because
a rejected value is somebody's personal data.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Annotated, Final, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

_BREAKS: Final = frozenset({"Cc", "Zl", "Zp"})
_LINE_BREAKS: Final = "\n\r\x0b\x0c\x85\u2028\u2029"

# The characters RFC 5322 allows unquoted in the local part (the HTML ``type=email``
# set), joined by single dots; a domain of at least two labels ending in a real top level
# domain or its punycode form. Ascii only: an address we cannot put in a header as written
# is one we cannot reply to.
_ATOM: Final = r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
_LABEL: Final = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_TLD: Final = r"(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})"
_EMAIL: Final = re.compile(_ATOM + r"(?:\." + _ATOM + r")*@(?:" + _LABEL + r"\.)+" + _TLD)

MAX_EMAIL_LENGTH: Final = 254
MAX_LOCAL_PART_LENGTH: Final = 64


def clean_line(value: str) -> str:
    """One line of text: each control character or line break becomes a space, lone
    surrogates (which no database can store) are dropped, runs of whitespace collapse to
    one space and the ends are trimmed."""
    spaced = "".join(
        " " if unicodedata.category(char) in _BREAKS else char
        for char in value
        if unicodedata.category(char) != "Cs"
    )
    return " ".join(spaced.split())


def clean_text(value: str) -> str:
    """Several lines of text: every kind of line break becomes a plain newline, tabs stay,
    any other control character and lone surrogates are dropped, and the ends are trimmed."""
    kept: list[str] = []
    for char in value.replace("\r\n", "\n"):
        if char in _LINE_BREAKS:
            kept.append("\n")
        elif char == "\t" or unicodedata.category(char) not in {"Cc", "Cs"}:
            kept.append(char)
    return "".join(kept).strip()


def _line(value: object) -> object:
    return clean_line(value) if isinstance(value, str) else value


def _text(value: object) -> object:
    return (clean_text(value) or None) if isinstance(value, str) else value


def _blank_to_none(value: object) -> object:
    """An optional field left empty is a field not given."""
    if isinstance(value, str):
        return value.strip() or None
    return value


def _email_text(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


def _email_shape(value: str) -> str:
    local, _, _ = value.partition("@")
    if len(local) > MAX_LOCAL_PART_LENGTH or not _EMAIL.fullmatch(value):
        raise ValueError("not a valid email address")
    return value


def _path(value: str) -> str:
    if not value.startswith("/") or any(
        char.isspace() or unicodedata.category(char) in {"Cc", "Cs"} for char in value
    ):
        raise ValueError("page must be a path that starts with / and holds no spaces")
    return value


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DemoRequestIn(_Request):
    """What the website sends. See the module docstring for the contract's rules."""

    full_name: Annotated[str, BeforeValidator(_line), Field(min_length=2, max_length=120)]
    email: Annotated[
        str,
        BeforeValidator(_email_text),
        Field(max_length=MAX_EMAIL_LENGTH),
        AfterValidator(_email_shape),
    ]
    company: Annotated[str, BeforeValidator(_line), Field(min_length=1, max_length=160)]
    # The constraints sit on the ``str`` inside each optional, and the cleaner outside it:
    # a cleaner that turns an empty string into None must not hand None to a length check.
    message: Annotated[Annotated[str, Field(max_length=2000)] | None, BeforeValidator(_text)] = None
    interest: Annotated[
        Annotated[str, Field(max_length=64, pattern=r"^[a-z0-9][a-z0-9:_-]{0,63}$")] | None,
        BeforeValidator(_blank_to_none),
    ] = None
    """What the visitor was looking at, e.g. ``third-party-risk`` or ``pricing:team``."""

    source: Annotated[
        Annotated[str, Field(max_length=32, pattern=r"^[a-z0-9][a-z0-9_-]{0,31}$")] | None,
        BeforeValidator(_blank_to_none),
    ] = None
    """Which button on the site was clicked."""

    page: Annotated[
        Annotated[str, Field(max_length=200), AfterValidator(_path)] | None,
        BeforeValidator(_blank_to_none),
    ] = None
    """The path of the page the form was on."""

    website: str | None = None
    """The honeypot: a field no person sees and every form-filling script fills."""


class DemoRequestAccepted(BaseModel):
    status: Literal["received"] = "received"
