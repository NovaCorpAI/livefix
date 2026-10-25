#!/usr/bin/env python3
"""Measure how much live web search changes LiveFix's repair rate.

Each case under benchmark/cases/<name>/ is a tiny project with a failing test
caused by a real, documented, post-training-cutoff API change (see each case's
FIX.md). For every case the harness runs the LiveFix loop under two conditions,
identical except for one switch:

  web ON  : Tavily search feeds the model live documentation of the change.
  web OFF : the same model, same prompts, no web results.

It copies the case to a fresh temp dir per run (the agent edits files in place,
so every run must start from the broken code), checks the case really starts red,
runs the repair, and records whether the test ended green and how many iterations
it took. The gap between the ON and OFF columns is the value Tavily adds: these
fixes post-date common model cutoffs, so they are not reliably in the weights.

Requirements:
  - NEBIUS_API_KEY in the environment (and TAVILY_API_KEY for the web-ON column).
  - The per-case libraries in benchmark/requirements.txt, installed at versions
    that actually removed the old API.

Usage:
  python benchmark/run_benchmark.py                      # all cases, 1 run each
  python benchmark/run_benchmark.py --repeats 3          # 3 runs per condition
  python benchmark/run_benchmark.py --cases numpy_aliases pandas_append
  python benchmark/run_benchmark.py --web on             # only the web-ON column
  python benchmark/run_benchmark.py --self-test          # offline plumbing check
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# Make the repo root importable when this file is run directly as a script.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from livefix.agent import LiveFixAgent, run_test  # noqa: E402
from livefix.config import Config  # noqa: E402

HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
RESULTS_DIR = HERE / "results"
_IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")


def discover_cases(names: list[str] | None) -> list[tuple[Path, dict]]:
    cases: list[tuple[Path, dict]] = []
    for d in sorted(CASES_DIR.iterdir()):
        meta_path = d / "livefix_case.json"
        if not d.is_dir() or not meta_path.is_file():
            continue
        if names and d.name not in names:
            continue
        cases.append((d, json.loads(meta_path.read_text(encoding="utf-8"))))
    return cases


def run_once(case_dir: Path, meta: dict, config: Config, web_on: bool) -> dict:
    """Copy the case to a temp dir and run one repair. Returns a result dict."""
    test_command = meta.get("test_command", "python -m pytest -q")
    max_iters = int(meta.get("max_iters", 4))
    run_config = config if web_on else dataclasses.replace(config, tavily_api_key=None)
    with tempfile.TemporaryDirectory(prefix="livefix_bench_") as tmp:
        work = Path(tmp) / case_dir.name
        shutil.copytree(case_dir, work, ignore=_IGNORE)
        started_red = not run_test(work, test_command)[0]
        agent = LiveFixAgent(run_config, work, test_command)
        t0 = time.time()
        result = agent.run(max_iters=max_iters)
        elapsed = round(time.time() - t0, 1)
        return {
            "passed": bool(result.passed),
            "started_red": bool(started_red),
            "iterations": len(result.iterations),
            "used_search": any(it.hits for it in result.iterations),
            "elapsed_s": elapsed,
        }


def _rate(runs: list[dict]) -> str:
    if not runs:
        return "-"
    passed = sum(1 for r in runs if r["passed"])
    return f"{passed}/{len(runs)}"


def _markdown_table(rows: list[dict], conditions: list[str]) -> str:
    head = "| case | library | " + " | ".join(f"web {c}" for c in conditions) + " |"
    sep = "|" + "---|" * (2 + len(conditions))
    lines = [head, sep]
    for row in rows:
        cells = [row["case"], row["library"]]
        cells += [_rate(row["runs"][c]) for c in conditions]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def run_benchmark(cases, repeats: int, conditions: list[str]) -> list[dict]:
    config = Config.from_env()
    if "on" in conditions and not config.tavily_api_key:
        print("warning: TAVILY_API_KEY is not set, so the web-ON column is really "
              "web-OFF. Set it to measure the real gap.", file=sys.stderr)
    rows = []
    for case_dir, meta in cases:
        row = {"case": case_dir.name, "library": meta.get("library", "?"), "runs": {}}
        for cond in conditions:
            runs = []
            for n in range(repeats):
                print(f"  {case_dir.name} [web {cond}] run {n + 1}/{repeats} ...",
                      file=sys.stderr, flush=True)
                runs.append(run_once(case_dir, meta, config, web_on=(cond == "on")))
            row["runs"][cond] = runs
        rows.append(row)
    return rows


def self_test() -> int:
    """Validate the measurement plumbing offline, with a stubbed model.

    Exercises copy-to-temp, the red check, the loop, JSON parsing and file apply
    on the stdlib case, with no Nebius or Tavily call, so the harness itself can
    be trusted before any paid run.
    """
    case_dir = CASES_DIR / "py310_collections"
    meta = json.loads((case_dir / "livefix_case.json").read_text(encoding="utf-8"))
    fixed_app = (
        '"""Fixed: import Mapping from collections.abc."""\n\n'
        "from collections.abc import Mapping\n\n\n"
        "def count_keys(m):\n"
        "    if not isinstance(m, Mapping):\n"
        '        raise TypeError("expected a mapping")\n'
        "    return len(m)\n"
    )
    reply = json.dumps({"explanation": "collections.abc", "files": {"app.py": fixed_app}})

    dummy = Config(nebius_api_key="stub", nebius_base_url="http://localhost/v1/",
                   nebius_model="stub", tavily_api_key=None)
    test_command = meta["test_command"]
    with tempfile.TemporaryDirectory(prefix="livefix_selftest_") as tmp:
        work = Path(tmp) / case_dir.name
        shutil.copytree(case_dir, work, ignore=_IGNORE)
        started_red = not run_test(work, test_command)[0]
        agent = LiveFixAgent(dummy, work, test_command)
        agent.chat.complete = lambda system, user, temperature=0.1: reply  # type: ignore
        result = agent.run(max_iters=meta["max_iters"])
    ok = started_red and result.passed
    print(f"self-test: started_red={started_red} repaired={result.passed} "
          f"iterations={len(result.iterations)} -> {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cases", nargs="*", help="Case folder names to run (default: all).")
    parser.add_argument("--repeats", type=int, default=1, help="Runs per condition.")
    parser.add_argument("--web", choices=["on", "off", "both"], default="both",
                        help="Which web condition(s) to run.")
    parser.add_argument("--self-test", action="store_true",
                        help="Validate the harness offline with a stubbed model, then exit.")
    args = parser.parse_args(argv)

    if args.self_test:
        return self_test()

    conditions = ["on", "off"] if args.web == "both" else [args.web]
    cases = discover_cases(args.cases)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 2

    print(f"Running {len(cases)} case(s), {args.repeats} repeat(s), "
          f"conditions: {', '.join(conditions)}\n", file=sys.stderr)
    rows = run_benchmark(cases, args.repeats, conditions)

    table = _markdown_table(rows, conditions)
    print("\n" + table + "\n")

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {"generated_utc": stamp, "repeats": args.repeats,
               "conditions": conditions, "rows": rows}
    (RESULTS_DIR / f"{stamp}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8")
    (RESULTS_DIR / "latest.md").write_text(
        f"# LiveFix benchmark ({stamp})\n\n"
        f"Repeats per condition: {args.repeats}. Each cell is passed/total.\n\n"
        f"{table}\n", encoding="utf-8")
    print(f"wrote {RESULTS_DIR / (stamp + '.json')}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
