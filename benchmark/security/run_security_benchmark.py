#!/usr/bin/env python3
"""Measure whether live web search lets the model remediate a 2026 CVE.

The remediation task here is the decision that a plain model cannot make from
its weights: given a vulnerable Python dependency and its advisory id, name the
minimal SAFE version to upgrade to. Every advisory in advisories.json was
disclosed in 2026, after current model cutoffs, so the fixed version is a fact
the model can only get from the live web.

For each advisory the harness asks the model under two conditions, identical
except for one switch:

  web ON  : Tavily feeds live advisory text (the fixed-version fact).
  web OFF : the same model, same prompt, no web results.

The model is given only the package name and advisory id (and the web excerpts
when ON). It never sees the ground-truth fixed version. We grade the answer as
`fixed` (a known fixed version, or any version at or above min_safe), `wrong`
(a version that does not resolve the advisory), or `abstained` (the model
honestly says it does not know). The gap between ON and OFF is the value Tavily
adds; abstaining is the honest failure we expect from OFF.

Usage:
  python benchmark/security/run_security_benchmark.py                 # all, 1 run each
  python benchmark/security/run_security_benchmark.py --repeats 3
  python benchmark/security/run_security_benchmark.py --web on
  python benchmark/security/run_security_benchmark.py --ids pillow-CVE-2026-112398
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from livefix.config import Config  # noqa: E402
from livefix.nebius_client import NebiusChat  # noqa: E402
from livefix.search import WebSearch  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "advisories.json"
RESULTS_DIR = HERE / "results"

SYSTEM = (
    "You are a security remediation assistant. Given a software dependency (with "
    "its package ecosystem) and a vulnerability advisory id, plus optional live "
    "web search excerpts, name the minimal SAFE version to upgrade the package to "
    "so the advisory is fixed. Do "
    "not guess: if you cannot determine it, return null and confident=false. Reply "
    "with ONE JSON object and nothing else: "
    '{"package": "...", "safe_version": "X.Y.Z" or null, "confident": true/false, '
    '"source": "<url or none>"}.'
)


def _parse(reply: str) -> dict:
    for i, ch in enumerate(reply):
        if ch == "{":
            try:
                data, _ = json.JSONDecoder(strict=False).raw_decode(reply[i:])
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                continue
    return {}


def _ask(chat: NebiusChat, adv: dict, hits) -> dict:
    parts = [
        f"Package: {adv['package']} (ecosystem: {adv.get('ecosystem', 'PyPI')})\n",
        f"Advisory: {adv['advisory']} ({adv['note']})\n\n",
        "## Live web search results\n",
    ]
    if hits:
        for h in hits:
            parts.append(f"\n- {h.title} ({h.url})\n{h.content}\n")
    else:
        parts.append("\n(no web results available)\n")
    try:
        reply = chat.complete(SYSTEM, "".join(parts), temperature=0.0)
    except Exception as exc:  # transient API failure: treat as an abstain this run
        return {"safe_version": None, "confident": False, "error": type(exc).__name__}
    return _parse(reply)


def _grade(answer: dict, adv: dict) -> str:
    raw = answer.get("safe_version")
    if not raw:
        return "abstained"
    try:
        proposed = Version(str(raw))
    except InvalidVersion:
        return "wrong"
    if str(raw) in adv["fixed_versions"]:
        return "fixed"
    try:
        if proposed >= Version(adv["min_safe"]):
            return "fixed"
    except InvalidVersion:
        pass
    return "wrong"


def run(advisories, repeats: int, conditions: list[str]) -> list[dict]:
    config = Config.from_env()
    if "on" in conditions and not config.tavily_api_key:
        print("warning: TAVILY_API_KEY not set; the web-ON column is really OFF.",
              file=sys.stderr)
    chat = NebiusChat(config)
    search = WebSearch(config.tavily_api_key)
    rows = []
    for adv in advisories:
        row = {"id": adv["id"], "package": adv["package"], "results": {}}
        for cond in conditions:
            outcomes = []
            for n in range(repeats):
                print(f"  {adv['id']} [web {cond}] run {n + 1}/{repeats} ...",
                      file=sys.stderr, flush=True)
                hits = search.search(adv["query"]) if cond == "on" else []
                answer = _ask(chat, adv, hits)
                outcomes.append({
                    "grade": _grade(answer, adv),
                    "safe_version": answer.get("safe_version"),
                    "confident": answer.get("confident"),
                    "n_hits": len(hits),
                })
            row["results"][cond] = outcomes
        rows.append(row)
    return rows


def _tally(outcomes: list[dict]) -> str:
    fixed = sum(1 for o in outcomes if o["grade"] == "fixed")
    return f"{fixed}/{len(outcomes)}"


def _table(rows, conditions) -> str:
    head = "| advisory | package | " + " | ".join(f"web {c} (remediated)" for c in conditions) + " |"
    sep = "|" + "---|" * (2 + len(conditions))
    lines = [head, sep]
    for r in rows:
        cells = [r["id"], r["package"]] + [_tally(r["results"][c]) for c in conditions]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ids", nargs="*", help="Advisory ids to run (default: all).")
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--web", choices=["on", "off", "both"], default="both")
    args = ap.parse_args(argv)

    data = json.loads(DATA.read_text(encoding="utf-8"))["advisories"]
    if args.ids:
        data = [a for a in data if a["id"] in args.ids]
    if not data:
        print("no advisories selected", file=sys.stderr)
        return 2
    conditions = ["on", "off"] if args.web == "both" else [args.web]

    print(f"Remediating {len(data)} advisory(ies), {args.repeats} repeat(s), "
          f"conditions: {', '.join(conditions)}\n", file=sys.stderr)
    rows = run(data, args.repeats, conditions)

    table = _table(rows, conditions)
    print("\n" + table + "\n")
    # honest breakdown: how OFF fails (abstain vs wrong)
    for r in rows:
        for cond in conditions:
            grades = [o["grade"] for o in r["results"][cond]]
            print(f"  {r['id']} [{cond}]: {grades}", file=sys.stderr)

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (RESULTS_DIR / f"{stamp}.json").write_text(
        json.dumps({"generated_utc": stamp, "repeats": args.repeats,
                    "conditions": conditions, "rows": rows}, indent=2),
        encoding="utf-8")
    (RESULTS_DIR / "latest.md").write_text(
        f"# LiveFix security remediation benchmark ({stamp})\n\n"
        f"Repeats per condition: {args.repeats}. Each cell is "
        f"correctly-remediated / total (named a known-safe version).\n\n{table}\n",
        encoding="utf-8")
    print(f"wrote {RESULTS_DIR / (stamp + '.json')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
