"""Offline tests for the remediation signature (livefix/attest.py).

No network, no keys: they build a RemediationResult by hand and check the PR
title, body and commit trailer. The point is the signature stays honest (it
never claims a human review) and machine-readable.
"""
from livefix.agent import Iteration, RunResult
from livefix.remediate import RemediationResult, Resolution
from livefix import attest


def _result(passed: bool = True) -> RemediationResult:
    res = Resolution(
        safe_version="13.0.0",
        confident=True,
        source="https://explore.alas.aws.amazon.com/CVE-2026-112398.html",
        hits=[],
    )
    it = Iteration(
        index=1, passed=True, error_excerpt="AttributeError", query="q", hits=[],
        changed=["app.py"],
        explanation="Replaced product_name with ImageCms.getProfileName",
    )
    run = RunResult(passed=passed, iterations=[it])
    return RemediationResult(
        advisory="CVE-2026-112398", package="pillow", resolution=res,
        pin_before="pillow==12.3.0", pin_after="pillow>=13.0.0",
        repair=run, passed=passed,
    )


def test_pr_title():
    assert attest.pr_title(_result()) == "Security remediation: CVE-2026-112398 in pillow"


def test_commit_trailer_is_machine_readable():
    t = attest.commit_trailer(_result(), trace_url="https://smith.example/t/1")
    assert "LiveFix-Remediation: CVE-2026-112398" in t
    assert "LiveFix-Package: pillow" in t
    assert "LiveFix-Safe-Version: 13.0.0" in t
    assert "LiveFix-Verified: tests-pass" in t
    assert "LiveFix-Trace: https://smith.example/t/1" in t
    assert "LiveFix-Maker: NovaCorp Labs" in t


def test_pr_body_is_honest_and_compact():
    body = attest.pr_body(_result())
    assert "Verified by LiveFix · NovaCorp Labs · novacorplabs.com" in body
    assert "<details><summary>What LiveFix did</summary>" in body
    assert "13.0.0" in body
    assert "pillow>=13.0.0" in body
    assert "app.py" in body
    # Honest by construction: it must never imply a human reviewed the change.
    assert "reviewed by" not in body.lower()


def test_unverified_when_tests_fail():
    body = attest.pr_body(_result(passed=False))
    assert "needs a human" in body
    assert "LiveFix-Verified: unverified" in attest.commit_trailer(_result(passed=False))
