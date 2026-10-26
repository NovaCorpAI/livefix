"""End-to-end vulnerability remediation.

A security bump is two problems, not one. First, *which* version is safe: for a
CVE disclosed after the model's training cutoff, that fact lives only on the live
web, and a plain model cannot supply it (it abstains or guesses). Second, the
safe version often changes an API, so the upgrade that closes the CVE breaks the
build, which is why so many Dependabot bump PRs rot unmerged.

LiveFix closes both in one pass:

  1. Resolve  : search the live web (Tavily) and have the NVIDIA Nemotron model
                on Nebius Token Factory name the minimal safe version. This is the
                step the weights cannot do for a fresh CVE.
  2. Bump     : pin the dependency to that version in the manifest.
  3. Repair   : run the LiveFix repair loop to fix whatever the upgrade broke,
                verified by the project's own tests.

The result is a green, merge-ready change instead of a red bump PR.

Run it directly:
  python -m livefix.remediate --project DIR --package pillow \
      --advisory CVE-2026-112398 --test "python -m pytest -q"
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .agent import LiveFixAgent, RunResult
from .config import Config
from .nebius_client import NebiusChat
from .search import SearchHit, WebSearch
from .tracing import traceable

_RESOLVE_SYSTEM = (
    "You are a security remediation assistant. Given a Python package and a "
    "vulnerability advisory id, plus optional live web search excerpts, name the "
    "minimal SAFE version to upgrade the package to so the advisory is fixed. Do "
    "not guess: if you cannot determine it from the material, return null and "
    "confident=false. Reply with ONE JSON object and nothing else: "
    '{"package": "...", "safe_version": "X.Y.Z" or null, "confident": true/false, '
    '"source": "<url or none>"}.'
)


def _parse_json(reply: str) -> dict:
    for i, ch in enumerate(reply):
        if ch == "{":
            try:
                data, _ = json.JSONDecoder(strict=False).raw_decode(reply[i:])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    return {}


@dataclass
class Resolution:
    safe_version: str | None
    confident: bool
    source: str
    hits: list[SearchHit] = field(default_factory=list)


@traceable(name="livefix.resolve_safe_version")
def resolve_safe_version(
    chat: NebiusChat, search: WebSearch, package: str, advisory: str, note: str = ""
) -> Resolution:
    """Find the minimal safe version for an advisory, grounded in live search."""
    query = f"{package} {advisory} fixed safe version patch"
    hits = search.search(query)
    parts = [
        f"Package: {package}\n",
        f"Advisory: {advisory}" + (f" ({note})" if note else "") + "\n\n",
        "## Live web search results\n",
    ]
    if hits:
        for h in hits:
            parts.append(f"\n- {h.title} ({h.url})\n{h.content}\n")
    else:
        parts.append("\n(no web results available)\n")
    reply = chat.complete(_RESOLVE_SYSTEM, "".join(parts), temperature=0.0)
    data = _parse_json(reply)
    raw = data.get("safe_version")
    return Resolution(
        safe_version=str(raw) if raw else None,
        confident=bool(data.get("confident")),
        source=str(data.get("source", "none")),
        hits=hits,
    )


# A requirements line like `Pillow==12.3.0  # comment` or `pillow>=11,<12`.
def _pin_line_re(package: str) -> re.Pattern:
    return re.compile(
        rf"^(?P<indent>\s*)(?P<name>{re.escape(package)})\s*(?P<spec>[^#\s].*?)?"
        rf"(?P<comment>\s*#.*)?$",
        re.IGNORECASE,
    )


def bump_pin(manifest_path: Path, package: str, safe_version: str) -> tuple[str | None, str | None]:
    """Pin `package` to `>=safe_version` in a requirements file.

    Returns (old_line, new_line); (None, None) if the package is not listed.
    """
    if not manifest_path.is_file():
        return None, None
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    pat = _pin_line_re(package)
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        m = pat.match(line)
        if not m:
            continue
        indent = m.group("indent") or ""
        comment = m.group("comment") or ""
        new_line = f"{indent}{package}>={safe_version}{comment}"
        if new_line == line:
            return line, None  # already satisfied
        old = line
        lines[idx] = new_line
        manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return old, new_line
    return None, None


@dataclass
class RemediationResult:
    advisory: str
    package: str
    resolution: Resolution
    pin_before: str | None
    pin_after: str | None
    repair: RunResult | None
    passed: bool


class Remediator:
    def __init__(self, config: Config, project_dir, test_command: str,
                 manifest: str = "requirements.txt"):
        self.config = config
        self.project_dir = Path(project_dir).resolve()
        self.test_command = test_command
        self.manifest = manifest
        self.chat = NebiusChat(config)
        self.search = WebSearch(config.tavily_api_key)

    @traceable(name="livefix.remediate")
    def remediate(self, package: str, advisory: str, note: str = "") -> RemediationResult:
        res = resolve_safe_version(self.chat, self.search, package, advisory, note)
        if not res.safe_version:
            # Without the post-cutoff fact there is nothing safe to bump to.
            return RemediationResult(advisory, package, res, None, None, None, False)

        manifest_path = (self.project_dir / self.manifest).resolve()
        try:
            manifest_path.relative_to(self.project_dir)  # never write outside the project
        except ValueError:
            manifest_path = self.project_dir / "requirements.txt"
        before, after = bump_pin(manifest_path, package, res.safe_version)

        # Fix whatever the upgrade broke, verified by the project's own tests.
        repair = LiveFixAgent(self.config, self.project_dir, self.test_command).run()
        return RemediationResult(advisory, package, res, before, after, repair, repair.passed)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="livefix.remediate",
        description="Resolve the safe version for a CVE from the live web, bump the "
        "dependency, and repair any code the upgrade breaks.")
    ap.add_argument("--project", required=True, help="Path to the project to remediate.")
    ap.add_argument("--package", required=True, help="Vulnerable package name.")
    ap.add_argument("--advisory", required=True, help="CVE or GHSA id.")
    ap.add_argument("--note", default="", help="Short advisory description (optional).")
    ap.add_argument("--test", required=True, help='Test command, e.g. "python -m pytest -q".')
    ap.add_argument("--manifest", default="requirements.txt", help="Dependency manifest filename.")
    ap.add_argument("--emit-dir", default=None,
                    help="Write the PR title, body and commit trailer here (for the GitHub Action).")
    args = ap.parse_args(argv)

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project dir not found: {project}", file=sys.stderr)
        return 2

    config = Config.from_env()
    rem = Remediator(config, project, args.test, args.manifest)
    print(f"LiveFix remediation on {project}")
    print(f"  model: {config.nebius_model}")
    print(f"  web search: {'on (Tavily)' if rem.search.enabled else 'off'}")
    print(f"  advisory: {args.advisory}  package: {args.package}\n")

    result = rem.remediate(args.package, args.advisory, args.note)

    if args.emit_dir:
        from . import attest  # local import avoids a circular import at module load
        import os
        emit = Path(args.emit_dir)
        emit.mkdir(parents=True, exist_ok=True)
        trace_url = os.environ.get("LIVEFIX_TRACE_URL") or None
        (emit / "pr_title.txt").write_text(attest.pr_title(result), encoding="utf-8")
        (emit / "pr_body.md").write_text(attest.pr_body(result, trace_url), encoding="utf-8")
        (emit / "commit_trailer.txt").write_text(
            attest.commit_trailer(result, trace_url), encoding="utf-8")
        (emit / "verified.txt").write_text(
            "true" if result.passed else "false", encoding="utf-8")
        (emit / "safe_version.txt").write_text(
            result.resolution.safe_version or "", encoding="utf-8")

    r = result.resolution
    print("1. Resolve safe version (live web)")
    if result.resolution.safe_version:
        print(f"   -> {args.package} safe at {r.safe_version}  "
              f"(confident={r.confident}, source: {r.source})")
        if r.hits:
            print(f"   grounded on {len(r.hits)} source(s); e.g. {r.hits[0].url}")
    else:
        print("   -> model could not determine a safe version from the web; "
              "nothing to bump. (A plain model abstains here.)")
        return 1

    print("2. Bump the dependency pin")
    if result.pin_after:
        print(f"   {args.manifest}: '{(result.pin_before or '').strip()}' -> "
              f"'{result.pin_after.strip()}'")
    elif result.pin_before:
        print(f"   {args.manifest}: already pinned safe ('{result.pin_before.strip()}')")
    else:
        print(f"   {args.package} not found in {args.manifest}; skipped the pin edit")

    print("3. Repair code the upgrade broke")
    if result.repair:
        for it in result.repair.iterations:
            tag = "PASS" if it.passed else "fail"
            line = f"   [iter {it.index}] {tag}"
            if it.changed:
                line += f"  changed: {', '.join(it.changed)}"
            print(line)
            if it.explanation:
                print(f"       note: {it.explanation}")
    print()
    if result.passed:
        print(f"RESULT: {args.advisory} remediated. Pin bumped and tests pass.")
        return 0
    print(f"RESULT: {args.advisory} not fully remediated; inspect the steps above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
