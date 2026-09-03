"""Remediation-plan generation invariants (the pure heuristic + red flags)."""

from verity.modules.vulnerabilities.remediation import (
    RemediationContext,
    heuristic_plan,
    red_flags,
)


def _ctx(**over: object) -> RemediationContext:
    base: dict[str, object] = {
        "cve_id": "CVE-2021-44228",
        "title": "Log4Shell",
        "severity": "critical",
        "cvss_score": 10.0,
        "recommendation": None,
        "fixed_versions": "log4j 2.17.1",
        "patch_available": True,
        "kev_flag": True,
        "epss_score": 0.97,
        "public_exploit_count": 5,
        "risk_score": 100.0,
        "overdue": True,
        "asset_name": "web-01",
        "asset_tier": "critical",
        "internet_facing": True,
    }
    base.update(over)
    return RemediationContext(**base)  # type: ignore[arg-type]


def test_patch_plan_names_the_fixed_version() -> None:
    plan = heuristic_plan(_ctx())
    assert plan.fix_type == "patch"
    assert "2.17.1" in plan.fix_artifact
    assert plan.rollback_plan


def test_no_patch_falls_back_to_mitigation() -> None:
    plan = heuristic_plan(
        _ctx(
            cve_id=None,
            title="Weak TLS",
            severity="medium",
            cvss_score=5.0,
            fixed_versions=None,
            patch_available=None,
            kev_flag=False,
            epss_score=0.01,
            public_exploit_count=None,
            asset_tier="low",
            internet_facing=False,
        )
    )
    assert plan.fix_type == "mitigation"


def test_red_flags_capture_the_act_now_signals() -> None:
    flags = red_flags(_ctx())
    assert any("Known Exploited" in f for f in flags)
    assert any("internet-facing" in f for f in flags)
