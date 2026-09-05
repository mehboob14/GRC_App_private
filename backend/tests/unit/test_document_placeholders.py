"""A template with placeholders left in it is not a policy — publishing one puts
`{{frequency}}` in front of an auditor. These check the two properties that
matter: nothing in ordinary policy prose is mistaken for a field, and filling in
what we know never touches what we do not."""

from __future__ import annotations

from verity.modules.documents.placeholders import AUTO_FILLED, fill, find


class TestFind:
    def test_counts_each_field_and_orders_by_frequency(self) -> None:
        html = "<p>{{company_name}} reviews access {{frequency}}. {{company_name}} logs it.</p>"

        found = find(html)

        assert [p.key for p in found] == ["company_name", "frequency"]
        assert found[0].count == 2
        assert found[1].count == 1

    def test_gives_a_human_label_for_shipped_fields(self) -> None:
        (freq,) = find("<p>every {{frequency}}</p>")
        assert freq.label == "How often (e.g. quarterly)"

    def test_falls_back_to_a_readable_label_for_unknown_fields(self) -> None:
        (other,) = find("<p>{{data_owner}}</p>")
        assert other.label == "Data owner"

    def test_tolerates_whitespace_inside_the_braces(self) -> None:
        assert [p.key for p in find("<p>{{ company_name }}</p>")] == ["company_name"]

    def test_nothing_to_find(self) -> None:
        assert find(None) == []
        assert find("") == []
        assert find("<p>A finished policy.</p>") == []


class TestDoesNotFlagOrdinaryProse:
    """False positives here are worse than misses: every one is a phantom task
    on somebody's checklist."""

    def test_single_braces_are_not_fields(self) -> None:
        assert find("<p>Set {x} to the value.</p>") == []

    def test_square_brackets_are_not_fields(self) -> None:
        # The upstream text uses [Optional] as an editorial marker, not a field.
        assert find("<p>[Optional] This section may be removed.</p>") == []

    def test_angle_brackets_and_html_are_not_fields(self) -> None:
        assert find("<p>Escalate to <strong>the owner</strong> within <sup>2</sup> hours.</p>") == []

    def test_currency_and_maths_are_not_fields(self) -> None:
        assert find("<p>Budget {{}} is not a field; ${{}} neither.</p>") == []


class TestFill:
    def test_replaces_only_what_it_was_given(self) -> None:
        html = "<p>{{company_name}} reviews access {{frequency}}.</p>"

        out = fill(html, {"company_name": "Northwind"})

        assert "Northwind" in out
        assert "{{frequency}}" in out, "a field with no answer must be left for a person"
        assert "{{company_name}}" not in out

    def test_is_case_insensitive_on_the_key(self) -> None:
        assert "Northwind" in fill("<p>{{Company_Name}}</p>", {"company_name": "Northwind"})

    def test_an_empty_value_is_not_an_answer(self) -> None:
        """Substituting "" would silently delete the placeholder and hide that a
        decision was never made."""
        out = fill("<p>{{company_name}}</p>", {"company_name": ""})
        assert out == "<p>{{company_name}}</p>"

    def test_fills_every_occurrence(self) -> None:
        out = fill("<p>{{company_name}} and {{company_name}}</p>", {"company_name": "Acme"})
        assert out.count("Acme") == 2
        assert find(out) == []

    def test_company_name_is_the_only_thing_filled_automatically(self) -> None:
        """The rest are judgements the customer has to make and then live up to."""
        assert AUTO_FILLED == {"company_name"}
