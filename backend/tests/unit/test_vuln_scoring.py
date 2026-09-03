"""Prioritisation invariants for the vulnerability risk score (ADR-0010 §3.9)."""

from verity.modules.vulnerabilities.scoring import AssetRisk, compute_risk


def test_exploited_critical_outranks_quiet_high() -> None:
    """An exploited, internet-facing critical must beat a quiet internal high even
    when the raw CVSS gap is small — that is the whole point of the blend."""
    exploited_crit, _ = compute_risk(
        severity="critical",
        cvss_score=9.8,
        epss_score=0.9,
        kev_flag=True,
        public_exploit_count=3,
        asset=AssetRisk("critical", internet_facing=True),
    )
    quiet_high, _ = compute_risk(
        severity="high",
        cvss_score=8.1,
        epss_score=0.01,
        kev_flag=False,
        public_exploit_count=0,
        asset=AssetRisk("low", internet_facing=False),
    )
    assert exploited_crit > quiet_high
    assert exploited_crit <= 100.0


def test_unknown_enrichment_degrades_never_zeroes() -> None:
    """A critical with no CVSS/EPSS/asset data still scores meaningfully — missing
    intel must not launder a critical into a low."""
    score, reason = compute_risk(
        severity="critical",
        cvss_score=None,
        epss_score=None,
        kev_flag=False,
        public_exploit_count=None,
        asset=AssetRisk(None),
    )
    assert score > 30.0
    assert "unrated" in reason


def test_kev_floors_to_top_band() -> None:
    """A known-exploited CVE never sits below the top priority band, even a
    low-CVSS one on a quiet internal asset — KEV is act-now."""
    score, reason = compute_risk(
        severity="low",
        cvss_score=3.1,
        epss_score=0.001,
        kev_flag=True,
        public_exploit_count=None,
        asset=AssetRisk("low", internet_facing=False),
    )
    assert score >= 75.0
    assert "KEV" in reason


def test_reason_names_the_drivers() -> None:
    _, reason = compute_risk(
        severity="critical",
        cvss_score=9.8,
        epss_score=0.9,
        kev_flag=True,
        public_exploit_count=3,
        asset=AssetRisk("critical", internet_facing=True),
    )
    assert "KEV" in reason
    assert "EPSS" in reason
