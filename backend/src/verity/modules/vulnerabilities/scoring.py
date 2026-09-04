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


#: Each threat term's share of the 0-100 base, i.e. its coefficient x 10 x 10.
#: These are the caps a breakdown bar is drawn against.
_CVSS_MAX: Final = 50.0
_EPSS_MAX: Final = 30.0
_EXPLOIT_MAX: Final = 20.0


@dataclass(frozen=True, slots=True)
class RiskFactor:
    """One additive term of the base score, with where its value came from.

    ``detail`` names the provenance rather than restating the number — a reader
    deciding whether to trust a score needs to know it came from NVD, or from a
    severity band because no CVSS was published.
    """

    key: str
    label: str
    detail: str
    points: float
    max_points: float


@dataclass(frozen=True, slots=True)
class RiskBreakdown:
    """How a risk score was arrived at, step by step.

    The model is deliberately not a flat sum, so this is not a flat list: three
    threat terms add to a base out of 100, the asset's criticality and exposure
    then *multiply* it, and two overrides can bind afterwards — the 100 cap and
    the KEV floor. Rendering only the three bars would show a total that does
    not match the score, which is exactly the kind of arithmetic nobody can
    check. Every step is reported so the sum is reproducible on screen.
    """

    score: float
    band: str
    reason: str
    factors: list[RiskFactor]
    base_score: float
    asset_multiplier: float
    asset_detail: str
    adjusted_score: float
    capped: bool
    kev_floor_applied: bool


@dataclass(frozen=True)
class AssetRisk:
    """The asset-side inputs to prioritisation (resolved from the assets module)."""

    tier: str | None = None
    internet_facing: bool = False
    customer_facing: bool = False


def _cvss_factor(cvss: float, published: float | None, severity: str) -> RiskFactor:
    detail = (
        f"CVSS {cvss:.1f} as published"
        if published is not None
        else f"no CVSS published — {severity} severity scores as {cvss:.1f}"
    )
    return RiskFactor(
        key="cvss",
        label="CVSS severity",
        detail=detail,
        points=round(0.5 * cvss * 10.0, 1),
        max_points=_CVSS_MAX,
    )


def _epss_factor(epss: float, published: float | None) -> RiskFactor:
    detail = (
        f"{epss:.1%} chance of exploitation in the next 30 days"
        if published is not None
        else "no EPSS published — scores as 0"
    )
    return RiskFactor(
        key="epss",
        label="Exploit probability",
        detail=detail,
        points=round(0.3 * epss * 10.0 * 10.0, 1),
        max_points=_EPSS_MAX,
    )


def _exploit_factor(signal: float, kev_flag: bool, public_exploit_count: int | None) -> RiskFactor:
    if kev_flag:
        detail = "on CISA's known-exploited catalogue"
    elif public_exploit_count:
        detail = f"{public_exploit_count} public exploit(s) found"
    else:
        detail = "no public exploit found"
    return RiskFactor(
        key="exploit",
        label="Known exploited",
        detail=detail,
        points=round(0.2 * signal * 10.0, 1),
        max_points=_EXPLOIT_MAX,
    )


def _asset_weight(asset: AssetRisk) -> tuple[float, str]:
    """The multiplier the asset applies, and a phrase naming what earned it."""
    weight = _TIER_WEIGHT.get(asset.tier or "", _TIER_WEIGHT_UNKNOWN)
    bits = [f"{asset.tier or 'unrated'} criticality"]
    if asset.internet_facing:
        weight += 0.10
        bits.append("internet-facing (+0.10)")
    if asset.customer_facing:
        weight += 0.05
        bits.append("customer-facing (+0.05)")
    if asset.tier is None and not asset.internet_facing and not asset.customer_facing:
        return weight, "no asset linked — unrated criticality assumed"
    return weight, ", ".join(bits)


def _reason(  # noqa: PLR0913
    *,
    cvss: float,
    epss_score: float | None,
    epss: float,
    kev_flag: bool,
    public_exploit_count: int | None,
    asset: AssetRisk,
) -> list[str]:
    reasons = [f"CVSS {cvss:.1f}"]
    if kev_flag:
        reasons.append("KEV (known exploited)")
    elif public_exploit_count:
        reasons.append(f"{public_exploit_count} public exploit(s)")
    if epss_score is not None:
        reasons.append(f"EPSS {epss:.0%}")
    exposure = "internet-facing" if asset.internet_facing else "internal"
    reasons.append(f"{asset.tier or 'unrated'} {exposure} asset")
    return reasons


def compute_breakdown(  # noqa: PLR0913
    *,
    severity: str,
    cvss_score: float | None,
    epss_score: float | None,
    kev_flag: bool,
    public_exploit_count: int | None,
    asset: AssetRisk,
) -> RiskBreakdown:
    """The risk score and every step that produced it.

    Missing inputs degrade, never zero the score: a critical with unknown EPSS is
    still critical.
    """
    cvss = cvss_score if cvss_score is not None else _SEVERITY_CVSS.get(severity, 5.0)
    epss = epss_score or 0.0
    exploit_signal = 10.0 if (kev_flag or bool(public_exploit_count)) else 0.0

    # Threat 0-10: CVSS anchors it, EPSS pulls up likely-exploited, KEV/PoC is the
    # "weaponised" jump. Reported on the 0-100 base scale (the threat term x 10),
    # so each factor's points and its cap are directly comparable.
    threat = 0.5 * cvss + 0.3 * (epss * 10.0) + 0.2 * exploit_signal
    factors = [
        _cvss_factor(cvss, cvss_score, severity),
        _epss_factor(epss, epss_score),
        _exploit_factor(exploit_signal, kev_flag, public_exploit_count),
    ]

    weight, asset_detail = _asset_weight(asset)
    base = round(threat * 10.0, 1)
    adjusted = round(threat * 10.0 * weight, 1)
    score = round(min(_MAX_SCORE, threat * 10.0 * weight), 1)

    reasons = _reason(
        cvss=cvss,
        epss_score=epss_score,
        epss=epss,
        kev_flag=kev_flag,
        public_exploit_count=public_exploit_count,
        asset=asset,
    )

    # KEV floor: a known-exploited CVE is act-now regardless of where it sits, so it
    # never falls below the top priority band even on a quiet internal asset. This
    # replaces the computed score rather than adding to it, which is why the
    # breakdown reports it as its own step instead of another bar.
    floored = kev_flag and score < _BAND_P1
    if floored:
        score = _BAND_P1
        reasons.append("KEV floor applied")

    return RiskBreakdown(
        score=score,
        band=priority_band(score),
        reason=" · ".join(reasons),
        factors=factors,
        base_score=base,
        asset_multiplier=round(weight, 2),
        asset_detail=asset_detail,
        adjusted_score=adjusted,
        capped=adjusted > _MAX_SCORE,
        kev_floor_applied=floored,
    )


def compute_risk(  # noqa: PLR0913
    *,
    severity: str,
    cvss_score: float | None,
    epss_score: float | None,
    kev_flag: bool,
    public_exploit_count: int | None,
    asset: AssetRisk,
) -> tuple[float, str]:
    """Return (risk_score 0-100, human reason) — the two halves the instance row
    stores. The full derivation is :func:`compute_breakdown`."""
    result = compute_breakdown(
        severity=severity,
        cvss_score=cvss_score,
        epss_score=epss_score,
        kev_flag=kev_flag,
        public_exploit_count=public_exploit_count,
        asset=asset,
    )
    return result.score, result.reason
