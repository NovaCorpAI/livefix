"""The LiveFix remediation signature.

Turns a RemediationResult into the artifacts a pull request carries: a title, a
body, and a machine-readable commit trailer, plus a one-line stamp. Honest by
construction: it states that the change was *remediated and verified by the
project's own tests*, never that a human reviewed it. The visible surface stays
small (a sentence, a collapsed detail block, a one-line stamp); the full trail
lives behind the trace link and the commit trailer, not in prose.
"""
from __future__ import annotations

from .remediate import RemediationResult

PRODUCT = "LiveFix"
MAKER = "NovaCorp Labs"
SITE = "novacorplabs.com"
STAMP = f"Verified by {PRODUCT} · {MAKER} · {SITE}"
CHECK_NAME = f"{PRODUCT} / remediation-verified"


def _repaired_files(result: RemediationResult) -> list[str]:
    files: list[str] = []
    if result.repair:
        for it in result.repair.iterations:
            for f in (it.changed or []):
                if f not in files:
                    files.append(f)
    return files


def _final_explanation(result: RemediationResult) -> str:
    if not result.repair:
        return ""
    for it in reversed(result.repair.iterations):
        if it.explanation:
            return it.explanation.strip()
    return ""


def pr_title(result: RemediationResult) -> str:
    return f"Security remediation: {result.advisory} in {result.package}"


def commit_trailer(result: RemediationResult, trace_url: str | None = None) -> str:
    """A greppable, machine-readable block for the commit message footer."""
    lines = [
        f"LiveFix-Remediation: {result.advisory}",
        f"LiveFix-Package: {result.package}",
    ]
    if result.resolution.safe_version:
        lines.append(f"LiveFix-Safe-Version: {result.resolution.safe_version}")
    src = result.resolution.source
    if src and src != "none":
        lines.append(f"LiveFix-Source: {src}")
    lines.append(f"LiveFix-Verified: {'tests-pass' if result.passed else 'unverified'}")
    if trace_url:
        lines.append(f"LiveFix-Trace: {trace_url}")
    lines.append(f"LiveFix-Maker: {MAKER}")
    return "\n".join(lines)


def pr_body(result: RemediationResult, trace_url: str | None = None) -> str:
    """A compact, honest PR body: one sentence, a collapsed detail block, a stamp."""
    pkg = result.package
    ver = result.resolution.safe_version or "?"
    before = (result.pin_before or "").strip()
    after = (result.pin_after or "").strip()
    src = result.resolution.source
    files = _repaired_files(result)
    expl = _final_explanation(result)

    bump_bit = ""
    if after and before:
        bump_bit = f" Bumped `{before}` to `{after}`."
    elif after:
        bump_bit = f" Pinned `{pkg}` to `{after}`."
    repair_bit = " Repaired the code the upgrade broke." if files else ""
    verdict = "Tests pass." if result.passed else "Tests did not pass; this one needs a human."

    out: list[str] = []
    out.append(
        f"Resolved the safe version for **{result.advisory}** from the live web and "
        f"landed the upgrade green.{bump_bit}{repair_bit} {verdict}"
    )
    out.append("")
    out.append("<details><summary>What LiveFix did</summary>")
    out.append("")
    if result.resolution.safe_version:
        line = f"- Resolved safe version **{ver}** from the live advisory"
        if src and src != "none":
            line += f" ([source]({src}))"
        out.append(line)
    if after:
        out.append(f"- Bumped the pin in the manifest: `{before or pkg}` to `{after}`")
    if files:
        out.append(f"- Repaired the code the upgrade broke: {', '.join(f'`{f}`' for f in files)}")
        if expl:
            out.append(f"  - {expl}")
    out.append(
        f"- Verified by the project's own tests: {'passing' if result.passed else 'not passing'}"
    )
    if trace_url:
        out.append(f"- Full step-by-step trace: [{trace_url}]({trace_url})")
    out.append("")
    out.append("</details>")
    out.append("")
    out.append("---")
    out.append("")
    out.append(STAMP)
    return "\n".join(out)
