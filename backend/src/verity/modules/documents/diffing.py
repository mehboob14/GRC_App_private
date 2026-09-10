"""What changed between two versions of a document's content.

Computed here rather than in the browser, for two reasons. The stored HTML is
never sanitised on the way in (it is sanitised on every render instead), so the
one thing a diff must not do is hand the client library-generated markup to
inject — these functions return tagged *text*, which the frontend renders as
ordinary React nodes and never through ``dangerouslySetInnerHTML``. And
``difflib`` is already in the standard library, so the alternative was a new
frontend dependency to redo work Python can already do.

The diff is deliberately two-level. Pairing whole blocks first — paragraphs,
headings, list items — means an edited sentence in the middle of a long clause
reads as *one changed paragraph with a few words highlighted*, instead of
"paragraph deleted, paragraph inserted". A reviewer signing off a policy will
not accept the latter, and a flat word diff over the whole document produces
exactly that as soon as anything is reordered.

Only authored HTML has text to compare. A version whose content came from an
uploaded PDF or Word file has ``content_html`` NULL and is reported as a whole
block that cannot be compared, rather than as an empty document.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from html.parser import HTMLParser
from typing import Final

#: Tags that end the current block. Anything else (em, strong, a, span) is
#: inline and its text joins the block it sits in — formatting-only changes are
#: deliberately invisible here, because the reader is being asked "what does it
#: say now", not "which tags moved".
_BLOCK_TAGS: Final[frozenset[str]] = frozenset(
    {
        "p",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "li",
        "blockquote",
        "pre",
        "tr",
        "td",
        "th",
        "section",
        "article",
        "header",
        "footer",
        "figcaption",
    }
)

#: Never render the contents of these, even though they are text nodes.
_SKIP_CONTENT: Final[frozenset[str]] = frozenset({"script", "style"})

_WS = re.compile(r"\s+")
#: Split on whitespace but keep punctuation attached, so "shall" and "shall,"
#: read as one changed word rather than two.
_WORD = re.compile(r"\S+")


@dataclass(frozen=True, slots=True)
class DiffSegment:
    """A run of words inside a block, and whether it survived the edit."""

    kind: str  # equal | added | removed
    text: str


@dataclass(frozen=True, slots=True)
class DiffBlock:
    """One paragraph/heading/list item, and what happened to it.

    ``changed`` blocks carry a mixed run of segments; the other kinds carry a
    single segment, so the frontend can render every block the same way.
    """

    kind: str  # equal | added | removed | changed
    tag: str
    segments: list[DiffSegment] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DiffSummary:
    """The counts a reader wants before deciding whether to read the diff."""

    blocks_added: int
    blocks_removed: int
    blocks_changed: int
    words_added: int
    words_removed: int

    @property
    def is_empty(self) -> bool:
        return not (self.blocks_added or self.blocks_removed or self.blocks_changed)


class _Blocks(HTMLParser):
    """Flatten HTML into ordered (tag, text) blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._tag = "p"
        self._buf: list[str] = []
        self._skip = 0

    def _flush(self) -> None:
        text = _WS.sub(" ", "".join(self._buf)).strip()
        if text:
            self.blocks.append((self._tag, text))
        self._buf = []

    def handle_starttag(self, tag: str, _attrs: object) -> None:
        if tag in _SKIP_CONTENT:
            self._skip += 1
            return
        if tag in _BLOCK_TAGS:
            self._flush()
            self._tag = tag
        elif tag == "br":
            self._buf.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_CONTENT:
            self._skip = max(0, self._skip - 1)
            return
        if tag in _BLOCK_TAGS:
            self._flush()
            self._tag = "p"

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self._buf.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def blocks(html: str | None) -> list[tuple[str, str]]:
    """Ordered (tag, text) blocks of an HTML body. Empty for None or no text."""
    if not html:
        return []
    parser = _Blocks()
    parser.feed(html)
    parser.close()
    return parser.blocks


def _word_segments(before: str, after: str) -> list[DiffSegment]:
    """Word-level diff inside one block that survived as a pair."""
    old = _WORD.findall(before)
    new = _WORD.findall(after)
    # autojunk drops any element appearing in more than 1% of a >200-item
    # sequence, which in prose means common words stop matching and the diff is
    # silently wrong on anything long.
    matcher = SequenceMatcher(None, old, new, autojunk=False)
    out: list[DiffSegment] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        words = old[i1:i2] if op in ("equal", "delete") else new[j1:j2]
        if not words:
            continue
        if op == "replace":
            out.append(DiffSegment(kind="removed", text=" ".join(old[i1:i2])))
            out.append(DiffSegment(kind="added", text=" ".join(new[j1:j2])))
            continue
        kind = {"equal": "equal", "delete": "removed", "insert": "added"}[op]
        out.append(DiffSegment(kind=kind, text=" ".join(words)))
    return out


def _whole(kind: str, tag: str, text: str) -> DiffBlock:
    return DiffBlock(kind=kind, tag=tag, segments=[DiffSegment(kind=kind, text=text)])


def diff_html(before: str | None, after: str | None) -> list[DiffBlock]:
    """Block-level diff of two HTML bodies, refined to words inside changed blocks."""
    old = blocks(before)
    new = blocks(after)
    matcher = SequenceMatcher(None, [b[1] for b in old], [b[1] for b in new], autojunk=False)

    out: list[DiffBlock] = []
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == "equal":
            out.extend(_whole("equal", t, x) for t, x in new[j1:j2])
        elif op == "delete":
            out.extend(_whole("removed", t, x) for t, x in old[i1:i2])
        elif op == "insert":
            out.extend(_whole("added", t, x) for t, x in new[j1:j2])
        else:
            # Pair replaced blocks positionally: the nth rewritten paragraph is
            # almost always the nth one. Any surplus on either side is a plain
            # insert or delete.
            pairs = min(i2 - i1, j2 - j1)
            for k in range(pairs):
                old_tag, old_text = old[i1 + k]
                new_tag, new_text = new[j1 + k]
                out.append(
                    DiffBlock(
                        kind="changed",
                        tag=new_tag or old_tag,
                        segments=_word_segments(old_text, new_text),
                    )
                )
            out.extend(_whole("removed", t, x) for t, x in old[i1 + pairs : i2])
            out.extend(_whole("added", t, x) for t, x in new[j1 + pairs : j2])
    return out


def summarise(diff: list[DiffBlock]) -> DiffSummary:
    """Counts for the one-line "what changed" label on a history row."""
    added = sum(1 for b in diff if b.kind == "added")
    removed = sum(1 for b in diff if b.kind == "removed")
    changed = sum(1 for b in diff if b.kind == "changed")
    words_added = sum(
        len(_WORD.findall(s.text)) for b in diff for s in b.segments if s.kind == "added"
    )
    words_removed = sum(
        len(_WORD.findall(s.text)) for b in diff for s in b.segments if s.kind == "removed"
    )
    return DiffSummary(
        blocks_added=added,
        blocks_removed=removed,
        blocks_changed=changed,
        words_added=words_added,
        words_removed=words_removed,
    )
