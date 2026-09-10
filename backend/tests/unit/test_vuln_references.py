"""These links exist so a reader can check a claim instead of trusting a badge.
The property that matters is therefore honesty: never a link to a KEV entry for a
CVE that is not on the catalogue, and never a derived link for an id the source
cannot resolve."""

from __future__ import annotations

import pytest

from verity.modules.vulnerabilities.references import Reference, build

LOG4SHELL = "CVE-2021-44228"


def _urls(refs: list[Reference], backs: str | None = None) -> list[str]:
    return [r.url for r in refs if backs is None or r.backs == backs]


def _build(**overrides: object) -> list[Reference]:
    kwargs: dict[str, object] = {
        "cve_id": LOG4SHELL,
        "kev_flag": False,
        "epss_score": None,
        "public_exploit_count": None,
        "exploit_refs": None,
        "advisory_url": None,
        "patch_source": None,
    }
    kwargs.update(overrides)
    return build(**kwargs)  # type: ignore[arg-type]


class TestOnlyLinksFactsThatExist:
    """A link to a source that does not mention this CVE wastes the reader's
    time and undermines the ones that do."""

    def test_no_kev_link_when_not_known_exploited(self) -> None:
        assert _urls(_build(kev_flag=False), "kev") == []

    def test_kev_links_when_known_exploited(self) -> None:
        urls = _urls(_build(kev_flag=True), "kev")
        assert any("known-exploited-vulnerabilities-catalog" in u for u in urls)
        assert any(u.endswith("known_exploited_vulnerabilities.json") for u in urls)
        assert all(LOG4SHELL in u or u.endswith(".json") for u in urls)

    def test_no_epss_link_without_a_score(self) -> None:
        assert _urls(_build(epss_score=None), "epss") == []

    def test_epss_link_when_scored(self) -> None:
        (url,) = _urls(_build(epss_score=0.97), "epss")
        assert url == f"https://api.first.org/data/v1/epss?cve={LOG4SHELL}"

    def test_epss_link_at_zero_because_zero_is_a_measurement(self) -> None:
        assert _urls(_build(epss_score=0.0), "epss")

    def test_no_exploitdb_link_without_a_known_exploit(self) -> None:
        assert not _urls(_build(public_exploit_count=0), "exploit")


class TestUnresolvableIds:
    @pytest.mark.parametrize(
        "cve",
        [
            "",
            None,
            "CVE-2024-123",
            "2024-1234",
            "cve 2024 1234",
            "MS17-010",
            "CVE-2021-44228, CVE-2021-45046",
        ],
    )
    def test_no_derived_links_for_an_id_the_sources_cannot_resolve(self, cve: str | None) -> None:
        refs = _build(cve_id=cve, kev_flag=True, epss_score=0.5, public_exploit_count=3)
        assert _urls(refs, "cve") == []
        assert _urls(refs, "kev") == []
        assert _urls(refs, "epss") == []
        assert _urls(refs, "exploit") == []

    def test_a_lowercase_id_still_resolves(self) -> None:
        refs = _build(cve_id="cve-2021-44228")
        assert all(LOG4SHELL in u for u in _urls(refs, "cve"))


class TestStoredSources:
    def test_proof_of_concept_repositories_are_linked(self) -> None:
        refs = _build(
            public_exploit_count=2,
            exploit_refs=[
                {
                    "full_name": "someone/log4shell-poc",
                    "url": "https://github.com/someone/log4shell-poc",
                    "stars": 431,
                }
            ],
        )
        poc = [r for r in refs if r.url.startswith("https://github.com/")]
        assert len(poc) == 1
        assert poc[0].label == "someone/log4shell-poc"
        assert "431" in poc[0].detail

    def test_a_non_https_reference_is_dropped(self) -> None:
        refs = _build(exploit_refs=[{"full_name": "x", "url": "javascript:alert(1)"}])
        assert not [r for r in refs if r.url.startswith("javascript")]

    def test_vendor_advisory_is_linked(self) -> None:
        (ref,) = [
            r
            for r in _build(
                advisory_url="https://msrc.microsoft.com/update-guide/vulnerability/CVE-2021-34527",
                patch_source="msrc",
            )
            if r.backs == "patch"
        ]
        assert "msrc.microsoft.com" in ref.url
        assert "msrc" in ref.detail

    def test_advisory_falling_back_to_nvd_is_not_shown_twice(self) -> None:
        """enrich defaults advisory_url to the NVD page when no vendor source was
        found; linking that again as a 'vendor advisory' would be a lie."""
        refs = _build(advisory_url=f"https://nvd.nist.gov/vuln/detail/{LOG4SHELL}")
        assert _urls(refs, "patch") == []


class TestSafety:
    def test_every_url_is_https(self) -> None:
        refs = _build(
            kev_flag=True,
            epss_score=0.9,
            public_exploit_count=1,
            exploit_refs=[{"full_name": "a/b", "url": "https://github.com/a/b", "stars": 1}],
            advisory_url="https://vendor.example/advisory",
        )
        assert refs
        assert all(r.url.startswith("https://") for r in refs)

    def test_every_reference_says_what_it_backs_and_why(self) -> None:
        refs = _build(kev_flag=True, epss_score=0.4, public_exploit_count=1)
        assert refs
        assert all(r.backs and r.label and r.detail for r in refs)
