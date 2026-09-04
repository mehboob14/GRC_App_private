"""The version diff has to answer "what exactly changed" to someone signing off a
policy, so these check the properties a reviewer relies on rather than the
implementation: an edited sentence stays one paragraph, formatting alone is not a
change, and an uploaded file is not mistaken for a deletion."""

from __future__ import annotations

from verity.modules.documents.diffing import blocks, diff_html, summarise


def _kinds(html_before: str | None, html_after: str | None) -> list[str]:
    return [b.kind for b in diff_html(html_before, html_after)]


class TestBlockPairing:
    """The reason the diff is block-level first: a mid-clause edit must read as
    one changed paragraph, not as a delete plus an insert."""

    def test_edited_sentence_stays_one_changed_block(self) -> None:
        before = (
            "<h2>Access control</h2>"
            "<p>Accounts are reviewed every quarter by the system owner.</p>"
            "<p>Unchanged closing paragraph.</p>"
        )
        after = before.replace("every quarter", "every month")

        result = diff_html(before, after)

        assert [b.kind for b in result] == ["equal", "changed", "equal"]
        changed = result[1]
        assert changed.tag == "p"
        assert [s.text for s in changed.segments if s.kind == "removed"] == ["quarter"]
        assert [s.text for s in changed.segments if s.kind == "added"] == ["month"]

    def test_untouched_words_are_reported_as_equal(self) -> None:
        result = diff_html("<p>The owner reviews access.</p>", "<p>The manager reviews access.</p>")

        (changed,) = result
        assert "".join(s.text for s in changed.segments if s.kind == "equal").strip()

    def test_list_items_diff_individually(self) -> None:
        assert _kinds("<ul><li>a</li><li>b</li></ul>", "<ul><li>a</li><li>c</li></ul>") == [
            "equal",
            "changed",
        ]

    def test_surplus_blocks_on_a_rewrite_are_plain_adds(self) -> None:
        kinds = _kinds("<p>one</p>", "<p>uno</p><p>dos</p>")
        assert kinds == ["changed", "added"]


class TestInsertAndDelete:
    def test_appended_paragraph(self) -> None:
        assert _kinds("<p>One.</p>", "<p>One.</p><p>Two.</p>") == ["equal", "added"]

    def test_deleted_paragraph(self) -> None:
        assert _kinds("<p>One.</p><p>Two.</p>", "<p>One.</p>") == ["equal", "removed"]

    def test_first_version_is_all_additions(self) -> None:
        assert _kinds(None, "<p>First draft.</p>") == ["added"]


class TestNoise:
    """Things that must NOT show up as a change, or the diff cries wolf and
    stops being read."""

    def test_inline_formatting_alone_is_not_a_change(self) -> None:
        kinds = _kinds(
            "<p>Text is <em>important</em>.</p>", "<p>Text is <strong>important</strong>.</p>"
        )
        assert all(k == "equal" for k in kinds)

    def test_whitespace_and_entities_normalise(self) -> None:
        assert all(k == "equal" for k in _kinds("<p>A &amp; B</p>", "<p>A\n   &amp;   B</p>"))

    def test_identical_content_reports_nothing_changed(self) -> None:
        stats = summarise(diff_html("<p>Same.</p>", "<p>Same.</p>"))
        assert stats.is_empty


class TestSafety:
    def test_script_content_never_becomes_diff_text(self) -> None:
        result = diff_html("<p>hi</p><script>alert(1)</script>", "<p>hi</p>")
        assert all("alert" not in s.text for b in result for s in b.segments)

    def test_style_content_never_becomes_diff_text(self) -> None:
        result = diff_html("<p>hi</p><style>p{color:red}</style>", "<p>hi</p>")
        assert all("color" not in s.text for b in result for s in b.segments)

    def test_segments_carry_text_only_never_markup(self) -> None:
        result = diff_html("<p>a <em>b</em> c</p>", "<p>a <em>z</em> c</p>")
        assert all("<" not in s.text for b in result for s in b.segments)


class TestUploadedFiles:
    def test_no_content_compares_to_nothing(self) -> None:
        assert diff_html(None, None) == []
        assert summarise([]).is_empty

    def test_empty_html_is_not_a_deletion(self) -> None:
        assert blocks("") == []
        assert blocks(None) == []


class TestSummary:
    def test_counts_words_and_blocks(self) -> None:
        stats = summarise(
            diff_html(
                "<p>Accounts are reviewed every quarter.</p><p>Second.</p>",
                "<p>Accounts are reviewed every month.</p><p>Second.</p><p>Third.</p>",
            )
        )
        assert stats.blocks_changed == 1
        assert stats.blocks_added == 1
        assert stats.blocks_removed == 0
        assert stats.words_added >= 1
        assert stats.words_removed >= 1
        assert not stats.is_empty

    def test_long_prose_still_matches_common_words(self) -> None:
        """difflib's autojunk drops elements appearing in >1% of a >200-item
        sequence, which in prose silently breaks the diff. It is disabled, and
        this is the guard on that."""
        body = " ".join(f"Clause {n} applies to the organisation and its staff." for n in range(60))
        before = f"<p>{body}</p>"
        after = f"<p>{body.replace('Clause 30', 'Clause thirty')}</p>"

        (changed,) = diff_html(before, after)

        assert changed.kind == "changed"
        # A working diff touches a couple of words; a broken one rewrites the lot.
        assert sum(len(s.text.split()) for s in changed.segments if s.kind != "equal") < 10
