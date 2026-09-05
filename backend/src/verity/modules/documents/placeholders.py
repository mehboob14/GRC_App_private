"""The `{{fields}}` a policy still needs someone to decide.

A shipped template is not a finished policy. It says things like "access reviews
are performed on a {{frequency}} basis" — that is a decision the customer has to
make and then live up to, and publishing it unfilled would put a placeholder in
front of an auditor.

So placeholders are tracked as first-class state: what remains, how many times
each appears, and whether it was something the platform could fill in on the
customer's behalf. The editor highlights them, and the document says how many
are left.

The syntax is the upstream library's own: ``{{snake_case}}``. Nothing else is
treated as a field, because guessing at square brackets or capitalised words
would flag ordinary policy prose.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Final

#: Deliberately narrow: braces around a snake_case word. Whitespace inside the
#: braces is tolerated because hand-editing introduces it.
PLACEHOLDER: Final = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}", re.IGNORECASE)

#: Fields the platform knows the answer to and fills in when a document is
#: created. Everything else is a judgement the customer has to make.
AUTO_FILLED: Final[frozenset[str]] = frozenset({"company_name"})

#: A human label for the ones we ship, so the editor's checklist reads as a
#: question rather than a variable name.
LABELS: Final[dict[str, str]] = {
    "company_name": "Company name",
    "frequency": "How often (e.g. quarterly)",
    "time": "How many business hours",
}


@dataclass(frozen=True, slots=True)
class Placeholder:
    """One field still to be decided, and how much of the document it affects."""

    key: str
    label: str
    count: int


def find(content_html: str | None) -> list[Placeholder]:
    """Every placeholder still present, most frequent first."""
    if not content_html:
        return []
    counts = Counter(m.group(1).lower() for m in PLACEHOLDER.finditer(content_html))
    return [
        Placeholder(key=key, label=LABELS.get(key, key.replace("_", " ").capitalize()), count=n)
        for key, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def fill(content_html: str, values: dict[str, str]) -> str:
    """Substitute the placeholders we have answers for, leaving the rest alone.

    Case-insensitive on the key, because ``{{Company_Name}}`` in a hand-edited
    document means the same thing to a reader and should mean the same here.
    """
    lowered = {k.lower(): v for k, v in values.items() if v}

    def swap(match: re.Match[str]) -> str:
        return lowered.get(match.group(1).lower(), match.group(0))

    return PLACEHOLDER.sub(swap, content_html)
