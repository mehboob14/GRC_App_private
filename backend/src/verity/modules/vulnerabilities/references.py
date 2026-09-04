"""Where each fact on a finding came from, as a link the reader can open.

A vulnerability page asserts a lot on a reader's trust: that this CVE is on
CISA's catalogue, that EPSS puts it in the 99th percentile, that a patch exists.
None of that is checkable from a badge. These are the primary sources behind each
claim, so an analyst — or an auditor asking how you knew — can go and look.

Every URL here is either stored on the record (a vendor advisory, a proof-of-
concept repository) or derived from the CVE id in that source's documented,
stable form. Nothing is guessed: a link is only emitted when the fact it backs is
actually present, so there is never a reference to a KEV entry for a CVE that is
not on the catalogue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

#: The canonical CVE form. Anything else — a vendor id, free text, several ids in
#: one field — is not resolvable at these sources, so it gets no derived links.
_CVE_RE: Final = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)

_NVD: Final = "https://nvd.nist.gov/vuln/detail/"
_CVE_ORG: Final = "https://www.cve.org/CVERecord?id="
_KEV_CATALOGUE: Final = (
    "https://www.cisa.gov/known-exploited-vulnerabilities-catalog?search_api_fulltext="
)
_KEV_FEED: Final = (
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
)
_EPSS_API: Final = "https://api.first.org/data/v1/epss?cve="
_EXPLOITDB: Final = "https://www.exploit-db.com/search?cve="


@dataclass(frozen=True, slots=True)
class Reference:
    """One primary source, and which claim on the page it backs."""

    #: Which fact this verifies: cve | kev | epss | exploit | patch
    backs: str
    label: str
    url: str
    #: Why a reader would open it, in one line.
    detail: str


def build(  # noqa: PLR0913 — one argument per fact that can carry a source
    *,
    cve_id: str | None,
    kev_flag: bool,
    epss_score: float | None,
    public_exploit_count: int | None,
    exploit_refs: list[dict[str, object]] | None,
    advisory_url: str | None,
    patch_source: str | None,
) -> list[Reference]:
    """The sources behind this finding, in the order a reader would work through
    them: what it is, whether it is being exploited, how likely, and the fix."""
    out: list[Reference] = []
    cve = (cve_id or "").strip().upper()
    resolvable = bool(_CVE_RE.match(cve))

    if resolvable:
        out.append(
            Reference(
                backs="cve",
                label="NVD record",
                url=f"{_NVD}{cve}",
                detail="The CVSS vector, weakness and affected products, from NIST.",
            )
        )
        out.append(
            Reference(
                backs="cve",
                label="CVE.org record",
                url=f"{_CVE_ORG}{cve}",
                detail="The original record as published by the assigning authority.",
            )
        )

    # Only link the catalogue when the finding actually claims KEV, or the link
    # is an invitation to search for something that is not there.
    if kev_flag and resolvable:
        out.append(
            Reference(
                backs="kev",
                label="CISA KEV catalogue",
                url=f"{_KEV_CATALOGUE}{cve}",
                detail="The catalogue entry behind the known-exploited badge.",
            )
        )
        out.append(
            Reference(
                backs="kev",
                label="KEV feed (JSON)",
                url=_KEV_FEED,
                detail="The machine-readable feed this platform reads, unmodified.",
            )
        )

    if epss_score is not None and resolvable:
        out.append(
            Reference(
                backs="epss",
                label="EPSS score (FIRST)",
                url=f"{_EPSS_API}{cve}",
                detail="Today's exploit-prediction score, straight from FIRST.",
            )
        )

    if public_exploit_count and resolvable:
        out.append(
            Reference(
                backs="exploit",
                label="Exploit-DB",
                url=f"{_EXPLOITDB}{cve}",
                detail="Published exploits recorded against this CVE.",
            )
        )

    # Proof-of-concept repositories, already stored by the GitHub search.
    for ref in exploit_refs or []:
        url = str(ref.get("url") or "").strip()
        if not url.startswith("https://"):
            continue
        name = str(ref.get("full_name") or "Proof of concept").strip()
        stars = ref.get("stars")
        out.append(
            Reference(
                backs="exploit",
                label=name,
                url=url,
                detail=(
                    f"Public proof-of-concept repository · {stars} stars"
                    if isinstance(stars, int)
                    else "Public proof-of-concept repository."
                ),
            )
        )

    # The vendor advisory is the one that says whether a fix exists. It defaults
    # to the NVD page when no vendor source was found, so only link it here when
    # it is genuinely a vendor's own advisory — otherwise it duplicates the NVD
    # entry already at the top.
    advisory = (advisory_url or "").strip()
    if advisory.startswith("https://") and not advisory.startswith(_NVD):
        out.append(
            Reference(
                backs="patch",
                label="Vendor advisory",
                url=advisory,
                detail=(
                    f"The vendor's own fix guidance ({patch_source})."
                    if patch_source
                    else "The vendor's own fix guidance."
                ),
            )
        )
    return out
