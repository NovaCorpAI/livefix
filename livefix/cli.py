"""Command-line entry point: `python -m livefix --project DIR --test "CMD"`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .agent import LiveFixAgent
from .config import Config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="livefix",
        description="Repair a failing test by grounding an NVIDIA Nemotron model "
        "(on Nebius Token Factory) with live web search (Tavily).",
    )
    parser.add_argument("--project", required=True, help="Path to the project to repair.")
    parser.add_argument(
        "--test", required=True,
        help='Command that runs the failing test, e.g. "python -m pytest -q".')
    parser.add_argument("--max-iters", type=int, default=5)
    args = parser.parse_args(argv)

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"error: project dir not found: {project}", file=sys.stderr)
        return 2

    config = Config.from_env()
    agent = LiveFixAgent(config, project, args.test)
    print(f"LiveFix on {project}")
    print(f"  model: {config.nebius_model}")
    print(f"  web search: {'on (Tavily)' if agent.search.enabled else 'off'}")
    print(f"  test: {args.test}\n")

    result = agent.run(max_iters=args.max_iters)

    for it in result.iterations:
        status = "PASS" if it.passed else "fail"
        print(f"[iter {it.index}] {status}")
        if it.query:
            print(f"    error: {it.query}")
            if it.hits:
                print(f"    grounded on {len(it.hits)} web result(s):")
                for h in it.hits[:2]:
                    print(f"      - {h.title}  <{h.url}>")
            else:
                print("    web search: no hits (or disabled)")
        if it.changed:
            print(f"    changed: {', '.join(it.changed)}")
        if it.explanation:
            print(f"    note: {it.explanation}")

    print()
    if result.passed:
        print("RESULT: test passes. LiveFix repaired the project.")
        return 0
    print("RESULT: still failing. Inspect the iterations above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
