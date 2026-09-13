"""What a policy still needs someone to fill in.

A shipped template is not a finished policy. It says things like "access reviews
are performed on a {{frequency}} basis", and it leaves written prompts such as
"<approver of requests for an exception to this policy, e.g., IT Manager>".
Both are decisions the customer has to make and then live up to, and publishing
either unfilled would put a placeholder in front of an auditor.

So placeholders are tracked as first-class state: what remains, how many times
each appears, and whether it was something the platform could fill in on the
customer's behalf. The editor and the viewer highlight them, and the document
says how many are left.

Two kinds are recognised, and deliberately nothing looser:

* ``field``: the upstream library's own ``{{snake_case}}`` syntax.
* ``prompt``: a written instruction to replace. In stored HTML the angle
  brackets of ``<approver ..., e.g., IT Manager>`` are escaped, so only escaped
  text can match and a real tag never does. A square-bracketed instruction of
  three or more words, like ``[party responsible for the code of conduct]``, is a
  prompt too. ``[Optional]`` markers are a keep-or-cut decision rather than a
  blank, and short brackets such as ``[1]`` or ``[RFC 2119]`` are references, so
  neither counts.
"""

from __future__ import annotations

import html
import re
from collections import Counter
from dataclasses import dataclass
from typing import Final

#: Deliberately narrow: braces around a snake_case word. Whitespace inside the
#: braces is tolerated because hand-editing introduces it.
PLACEHOLDER: Final = re.compile(r"\{\{\s*([a-z0-9_]+)\s*\}\}", re.IGNORECASE)

#: An escaped ``<prompt>`` that starts with a letter, digit, ``{`` or ``#``, so
#: "&lt; 5 minutes" (a space first) is not mistaken for one. One level of
#: nesting is allowed, because the templates write "<lock out after <6> failed
#: attempts>". It may not cross a line, which is what every tag is turned into
#: before matching, so it never spans two paragraphs.
PROMPT: Final = re.compile(
    r"&lt;([A-Za-z0-9{#](?:(?!&lt;|&gt;)[^\n]|&lt;(?:(?!&lt;|&gt;)[^\n]){1,80}?&gt;){0,299}?)&gt;"
)

#: A ``[bracketed instruction]`` that starts with a letter and is not an
#: ``[Optional ...]`` marker. The word count is checked separately.
BRACKET: Final = re.compile(r"\[(?!Optional)([A-Za-z][^\[\]\n]{2,199})\]")
_MIN_BRACKET_WORDS: Final = 3

_TAG: Final = re.compile(r"<[^>]+>")

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
    """One thing still to be filled in, and how much of the document it affects."""

    key: str
    label: str
    count: int
    #: ``field`` for ``{{snake_case}}``, ``prompt`` for written instructions.
    kind: str = "field"


def find(content_html: str | None) -> list[Placeholder]:
    """Every placeholder still present: fields first, then prompts, each most
    frequent first."""
    if not content_html:
        return []
    counts = Counter(m.group(1).lower() for m in PLACEHOLDER.finditer(content_html))
    fields = [
        Placeholder(key=key, label=LABELS.get(key, key.replace("_", " ").capitalize()), count=n)
        for key, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return fields + _prompts(content_html)


def _prompts(content_html: str) -> list[Placeholder]:
    # Tags become line breaks: a prompt cannot run across elements, and a real
    # tag can never be read as an escaped one.
    text = _TAG.sub("\n", content_html)
    counts: Counter[str] = Counter()
    labels: dict[str, str] = {}

    def add(inner: str) -> None:
        label = " ".join(html.unescape(inner).split())
        key = f"prompt:{label.lower()}"
        counts[key] += 1
        labels.setdefault(key, label)

    for match in PROMPT.finditer(text):
        add(match.group(1))
    for match in BRACKET.finditer(text):
        if len(match.group(1).split()) >= _MIN_BRACKET_WORDS:
            add(match.group(1))
    return [
        Placeholder(key=key, label=labels[key], count=n, kind="prompt")
        for key, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def fill(content_html: str, values: dict[str, str]) -> str:
    """Substitute the placeholders we have answers for, leaving the rest alone.

    Case-insensitive on the key, because ``{{Company_Name}}`` in a hand-edited
    document means the same thing to a reader and should mean the same here.
    Prompts are never filled: they are instructions for a person.
    """
    lowered = {k.lower(): v for k, v in values.items() if v}

    def swap(match: re.Match[str]) -> str:
        return lowered.get(match.group(1).lower(), match.group(0))

    return PLACEHOLDER.sub(swap, content_html)
