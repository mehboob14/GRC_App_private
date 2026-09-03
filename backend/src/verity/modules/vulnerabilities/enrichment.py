"""Live threat-intel enrichment for vulnerability definitions.

Two keyless public sources land at import and are refreshed daily:

* **EPSS** (FIRST.org) — the probability a CVE is exploited in the next 30 days,
  plus its percentile rank. Batched, one request for many CVEs.
* **CISA KEV** — the authoritative "known exploited in the wild" catalogue, with a
  ransomware sub-flag. Fetched whole and cached in-process (6h TTL).

**Public-exploit (GitHub PoC)** is opt-in: it needs a token and is rate-limited,
so it runs only when ``GITHUB_TOKEN`` is set and only from the daily job (not the
import hot path). Absent a token it returns "unknown" and KEV carries the
exploited-in-the-wild signal.

Every fetch degrades to empty on any error (timeout, offline, rate-limit) and
never raises — enrichment is best-effort decoration on top of the finding, never
a blocker. Nothing here writes the DB; the service persists the result.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import httpx

from verity.core.logging import get_logger

logger = get_logger(__name__)

_EPSS_URL = "https://api.first.org/data/v1/epss"
_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_GITHUB_SEARCH = "https://api.github.com/search/repositories"

_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
_CVE_IN_TEXT = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
_TIMEOUT = 10.0
_EPSS_BATCH = 100  # FIRST.org accepts a comma-joined batch; keep it modest.
_KEV_TTL = 6 * 3600
_GITHUB_REF_CAP = 5


@dataclass(frozen=True)
class Enrichment:
    epss_score: float | None = None
    epss_percentile: float | None = None
    kev_flag: bool = False
    kev_ransomware: bool = False
    kev_added_at: datetime | None = None
    public_exploit_count: int | None = None
    exploit_refs: list[dict[str, object]] = field(default_factory=list)
    # vendor patch intelligence (spec 128)
    patch_available: bool | None = None
    fixed_versions: str | None = None
    advisory_url: str | None = None
    patch_source: str | None = None
    # Per-source success: False means that source was unavailable this run, so the
    # caller must KEEP its previously-stored value rather than overwrite with empty.
    epss_ok: bool = False
    kev_ok: bool = False
    exploit_ok: bool = False


# in-process caches: (fetched_at, payload)
_kev_cache: tuple[float, dict[str, tuple[datetime | None, bool]]] | None = None
_exploitdb_cache: tuple[float, dict[str, int]] | None = None

_NVD_DETAIL = "https://nvd.nist.gov/vuln/detail/"
_NVD_API = "https://services.nvd.nist.gov/rest/json/2.0/cves/2.0"
_EXPLOITDB_CSV = "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv"
_MSRC_VULN = "https://api.msrc.microsoft.com/sug/v2.0/en-US/vulnerability/"
_EXPLOITDB_TTL = 24 * 3600


def is_cve(value: str | None) -> bool:
    return bool(value and _CVE_RE.match(value.strip()))


async def enrich_cves(
    cves: list[str], *, include_github: bool = False, include_patch: bool = False
) -> dict[str, Enrichment]:
    """Enrich a batch of CVE ids. Unknown/failed sources leave their fields None.
    Non-CVE inputs are dropped (nothing public to look up).

    Keyless sources (EPSS, KEV, Exploit-DB, the NVD advisory link) run always —
    including on the import hot path. GitHub PoC (needs a token) and the MSRC patch
    lookup run only when asked, from the daily job, to keep import fast."""
    wanted = sorted({c.strip().upper() for c in cves if is_cve(c)})
    if not wanted:
        return {}

    epss_raw, kev_raw, exploitdb_raw = await asyncio.gather(
        _fetch_epss(wanted), _fetch_kev(), _fetch_exploitdb(), return_exceptions=False
    )
    # None from a fetcher == that source was unavailable this run (so the caller
    # must keep the stored value); a dict (even empty) == the source answered.
    epss_ok, kev_ok, exploit_ok = (
        epss_raw is not None,
        kev_raw is not None,
        exploitdb_raw is not None,
    )
    epss, kev, exploitdb = epss_raw or {}, kev_raw or {}, exploitdb_raw or {}

    github: dict[str, tuple[int, list[dict[str, object]]]] = {}
    if include_github and _github_token():
        for cve in wanted:
            count_refs = await _github_poc(cve)
            if count_refs is not None:
                github[cve] = count_refs

    patch: dict[str, tuple[str | None, str | None]] = {}
    if include_patch:
        for cve in wanted:
            info = await _fetch_msrc(cve)
            if info is not None:
                patch[cve] = info

    out: dict[str, Enrichment] = {}
    for cve in wanted:
        e_score, e_pct = epss.get(cve, (None, None))
        kev_added, kev_ransom = kev.get(cve, (None, False))
        gh_count, gh_refs = github.get(cve, (None, []))
        edb_count = exploitdb.get(cve)
        # public exploit count: the richer of the keyless Exploit-DB baseline and
        # the opt-in GitHub search.
        counts = [c for c in (edb_count, gh_count) if c is not None]
        fixed_versions, advisory = patch.get(cve, (None, None))
        out[cve] = Enrichment(
            epss_score=e_score,
            epss_percentile=e_pct,
            kev_flag=cve in kev,
            kev_ransomware=kev_ransom,
            kev_added_at=kev_added,
            public_exploit_count=max(counts) if counts else None,
            exploit_refs=gh_refs,
            patch_available=True if fixed_versions else None,
            fixed_versions=fixed_versions,
            advisory_url=advisory or f"{_NVD_DETAIL}{cve}",
            patch_source="msrc" if fixed_versions else "nvd",
            epss_ok=epss_ok,
            kev_ok=kev_ok,
            exploit_ok=exploit_ok,
        )
    return out


async def _fetch_exploitdb() -> dict[str, int] | None:
    """CVE -> count of public exploits in the Exploit-DB archive. Keyless: the
    archive's index CSV, fetched whole and cached (24h). None == unavailable and no
    cache (keep stored exploit counts); a dict == authoritative."""
    global _exploitdb_cache  # noqa: PLW0603 — module-level TTL cache
    now = time.time()
    if _exploitdb_cache is not None and now - _exploitdb_cache[0] < _EXPLOITDB_TTL:
        return _exploitdb_cache[1]
    counts: dict[str, int] = {}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(_EXPLOITDB_CSV)
            resp.raise_for_status()
        for match in _CVE_IN_TEXT.finditer(resp.text):
            cve = match.group(0).upper()
            counts[cve] = counts.get(cve, 0) + 1
        _exploitdb_cache = (now, counts)
    except Exception:
        logger.warning("exploitdb_fetch_failed")
        return _exploitdb_cache[1] if _exploitdb_cache is not None else None
    return counts


@dataclass(frozen=True)
class NvdDetail:
    cvss_score: float | None = None
    cvss_vector: str | None = None
    cwe_id: str | None = None
    description: str | None = None


async def fetch_nvd(cve: str) -> NvdDetail | None:
    """Full NVD record for a CVE (CVSS base score/vector, primary CWE, English
    description) — for the manual-add CVE autofill. Keyless, best-effort; None on
    any failure or unknown CVE."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_NVD_API, params={"cveId": cve})
            if resp.status_code != httpx.codes.OK:
                return None
            data = resp.json()
        vulns = data.get("vulnerabilities") or []
        if not vulns:
            return None
        c = vulns[0].get("cve") or {}
        metrics = c.get("metrics") or {}
        score = vector = None
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            arr = metrics.get(key) or []
            if arr:
                cd = arr[0].get("cvssData") or {}
                score = _as_float(cd.get("baseScore"))
                vector = cd.get("vectorString")
                break
        cwe = None
        for w in c.get("weaknesses") or []:
            for d in w.get("description") or []:
                val = str(d.get("value", ""))
                if d.get("lang") == "en" and val.startswith("CWE-"):
                    cwe = val
                    break
            if cwe:
                break
        desc = next(
            (d.get("value") for d in c.get("descriptions") or [] if d.get("lang") == "en"), None
        )
        return NvdDetail(cvss_score=score, cvss_vector=vector, cwe_id=cwe, description=desc)
    except Exception:
        return None


async def _fetch_msrc(cve: str) -> tuple[str | None, str | None] | None:
    """Microsoft patch intelligence for a CVE: (fixed_versions summary, advisory
    url). Keyless MSRC Security Update Guide API; only Microsoft CVEs return data,
    everything else 404s and yields None. Best-effort."""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_MSRC_VULN}{cve}")
            if resp.status_code != httpx.codes.OK:
                return None
            body = resp.json()
        # Parse INSIDE the try — a 200 with a non-dict body (null / array / string)
        # must degrade to None, never raise out of enrichment (module contract).
        if not isinstance(body, dict):
            return None
        remediations = body.get("remediations") or body.get("Remediations") or []
        kbs = [
            str(r.get("description") or r.get("Description") or r.get("url") or "")
            for r in remediations
            if isinstance(r, dict)
        ]
        fixed = "; ".join(sorted({k for k in kbs if k})[:5]) or None
        advisory = f"https://msrc.microsoft.com/update-guide/vulnerability/{cve}"
    except Exception:
        return None
    return (fixed, advisory)


async def _fetch_epss(
    cves: list[str],
) -> dict[str, tuple[float | None, float | None]] | None:
    """None == the EPSS service was unavailable (keep stored values); a dict == it
    answered (a CVE absent from the dict genuinely has no EPSS)."""
    out: dict[str, tuple[float | None, float | None]] = {}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for start in range(0, len(cves), _EPSS_BATCH):
                batch = cves[start : start + _EPSS_BATCH]
                resp = await client.get(_EPSS_URL, params={"cve": ",".join(batch)})
                resp.raise_for_status()
                for row in resp.json().get("data", []):
                    cve = str(row.get("cve", "")).upper()
                    if cve:
                        out[cve] = (_as_float(row.get("epss")), _as_float(row.get("percentile")))
    except Exception:
        logger.warning("epss_fetch_failed", cve_count=len(cves))
        return None
    return out


async def _fetch_kev() -> dict[str, tuple[datetime | None, bool]] | None:
    """None == KEV was unavailable and no cache exists (keep stored kev_flag); a
    dict (fresh or cached) == authoritative, so a CVE absent from it is not KEV."""
    global _kev_cache  # noqa: PLW0603 — module-level TTL cache, single value
    now = time.time()
    if _kev_cache is not None and now - _kev_cache[0] < _KEV_TTL:
        return _kev_cache[1]
    catalogue: dict[str, tuple[datetime | None, bool]] = {}
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(_KEV_URL)
            resp.raise_for_status()
            for row in resp.json().get("vulnerabilities", []):
                cve = str(row.get("cveID", "")).upper()
                if not cve:
                    continue
                ransom = str(row.get("knownRansomwareCampaignUse", "")).lower() == "known"
                catalogue[cve] = (_as_date(row.get("dateAdded")), ransom)
        _kev_cache = (now, catalogue)
    except Exception:
        logger.warning("kev_fetch_failed")
        return _kev_cache[1] if _kev_cache is not None else None
    return catalogue


async def _github_poc(cve: str) -> tuple[int, list[dict[str, object]]] | None:
    """Count public proof-of-concept repos naming this CVE. Best-effort; a non-zero
    count means the exploit is no longer theoretical."""
    token = _github_token()
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                _GITHUB_SEARCH,
                params={"q": cve, "sort": "stars", "order": "desc", "per_page": _GITHUB_REF_CAP},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            resp.raise_for_status()
            body = resp.json()
            refs = [
                {
                    "full_name": r.get("full_name"),
                    "url": r.get("html_url"),
                    "stars": r.get("stargazers_count", 0),
                }
                for r in body.get("items", [])[:_GITHUB_REF_CAP]
            ]
            return int(body.get("total_count", 0)), refs
    except Exception:
        logger.warning("github_poc_fetch_failed")
        return None


def _github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    return token or None


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _as_date(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return None
