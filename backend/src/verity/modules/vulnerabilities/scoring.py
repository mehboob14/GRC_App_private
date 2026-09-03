"""Risk prioritisation and SLA math for vulnerability instances.

``risk_score`` (0-100) blends the definition's severity/CVSS and exploit
intelligence with the asset's criticality and exposure, so an exploited,
internet-facing, critical-asset instance outranks a higher-CVSS finding nobody is
exploiting (ER §3.9). Pure functions, so the daily recompute and the import path
share one implementation — and it carries its own self-check (run this file).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

_MAX_SCORE: Final = 100.0

# A severity with no numeric CVSS still needs a base; these are the band midpoints.
_SEVERITY_CVSS: dict[str, float] = {
    "critical": 9.5,
    "high": 7.5,
    "medium": 5.0,
    "low": 2.5,
    "info": 0.5,
}
# Asset criticality tier -> weight. "not assessed" sits between medium and high
# rather than laundering to a flattering low.
_TIER_WEIGHT: dict[str, float] = {"critical": 1.0, "high": 0.85, "medium": 0.65, "low": 0.5}
_TIER_WEIGHT_UNKNOWN = 0.7

# Default remediation SLA (days) per severity — CISA BOD 22-01 shape. None = no clock.
DEFAULT_SLA_DAYS: dict[str, int | None] = {
    "critical": 15,
    "high": 30,
    "medium": 60,
    "low": 90,
    "info": None,
}

# Priority bands (spec 129) — named buckets derived from the continuous risk score,
# so the register and the distribution dashboard group work by urgency, not by a
# raw number. P1 = act now.
PRIORITY_BANDS: tuple[str, ...] = ("P1", "P2", "P3", "P4")
_BAND_P1 = 75.0
_BAND_P2 = 50.0
_BAND_P3 = 25.0


def priority_band(risk_score: float | None) -> str:
    """Map a 0-100 risk score to a named priority bucket. Unscored → the lowest
    band rather than a flattering gap."""
    if risk_score is None:
        return "P4"
    if risk_score >= _BAND_P1:
        return "P1"
    if risk_score >= _BAND_P2:
        return "P2"
    if risk_score >= _BAND_P3:
        return "P3"
    return "P4"


@dataclass(frozen=True)
class AssetRisk:
    """The asset-side inputs to prioritisation (resolved from the assets module)."""

    tier: str | None = None
    internet_facing: bool = False
    customer_facing: bool = False


def compute_risk(  # noqa: PLR0913
    *,
    severity: str,
    cvss_score: float | None,
    epss_score: float | None,
    kev_flag: bool,
    public_exploit_count: int | None,
    asset: AssetRisk,
) -> tuple[float, str]:
    """Return (risk_score 0-100, human reason). Missing inputs degrade, never zero
    the score: a critical with unknown EPSS is still critical."""
    cvss = cvss_score if cvss_score is not None else _SEVERITY_CVSS.get(severity, 5.0)
    epss = epss_score or 0.0
    exploited = kev_flag or bool(public_exploit_count)
    exploit_signal = 10.0 if exploited else 0.0

    # Threat 0-10: CVSS anchors it, EPSS pulls up likely-exploited, KEV/PoC is the
    # "weaponised" jump.
    threat = 0.5 * cvss + 0.3 * (epss * 10.0) + 0.2 * exploit_signal

    weight = _TIER_WEIGHT.get(asset.tier or "", _TIER_WEIGHT_UNKNOWN)
    if asset.internet_facing:
        weight += 0.10
    if asset.customer_facing:
        weight += 0.05
    weight = min(weight, 1.20)

    score = round(min(_MAX_SCORE, threat * 10.0 * weight), 1)

    reasons: list[str] = [f"CVSS {cvss:.1f}"]
    if kev_flag:
        reasons.append("KEV (known exploited)")
    elif public_exploit_count:
        reasons.append(f"{public_exploit_count} public exploit(s)")
    if epss_score is not None:
        reasons.append(f"EPSS {epss:.0%}")
    tier_txt = asset.tier or "unrated"
    exposure = "internet-facing" if asset.internet_facing else "internal"
    reasons.append(f"{tier_txt} {exposure} asset")

    # KEV floor: a known-exploited CVE is act-now regardless of where it sits, so it
    # never falls below the top priority band even on a quiet internal asset.
    if kev_flag and score < _BAND_P1:
        score = _BAND_P1
        reasons.append("KEV floor applied")

    return score, " · ".join(reasons)
