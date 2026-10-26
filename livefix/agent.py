"""The LiveFix repair loop."""

from __future__ import annotations

import difflib
import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .nebius_client import NebiusChat
from .search import SearchHit, WebSearch
from .tracing import traceable

_TRACE_FILE_RE = re.compile(r'File "([^"]+)", line (\d+)')
# pytest renders intermediate frames as `<path>:<line>: in <func>` and the final
# exception location as `<path>:<line>: <ExceptionType>`. Match both by requiring
# only `:<line>: ` after the path; `.+?\.py` stops at the first .py so a Windows
# drive-letter colon (C:\...) does not break the match.
_PYTEST_FILE_RE = re.compile(r"^(.+?\.py):(\d+): \S", re.MULTILINE)
_FENCE_RE = re.compile(r"^```[a-zA-Z0-9_-]*\s*|\s*```$", re.MULTILINE)

_SYSTEM = (
    "You are LiveFix, a precise software-repair agent. You are given a failing "
    "test's output, the current contents of the project files named in the "
    "traceback, and excerpts from a live web search about the error. The usual "
    "cause is an API or dependency that changed after the code was written. "
    "Return the smallest edit that makes the test pass, grounded in the web "
    "excerpts (prefer the current, documented API over guesses). Reply with ONE "
    "JSON object and nothing else: "
    '{"explanation": "<one sentence>", "files": {"<relative/path>": "<full new '
    'file content>"}}. Only include files you actually change, and always give '
    "their COMPLETE new content, not a diff. Encode each file's content as a "
    'standard JSON string: escape every double quote as \\" and every newline as '
    "\\n. Never use triple quotes or Python string literals. Output only the JSON "
    "object, with no reasoning, commentary, or markdown before or after it."
)


@dataclass
class Iteration:
    index: int
    passed: bool
    error_excerpt: str
    query: str
    hits: list[SearchHit]
    changed: list[str]
    explanation: str
    diffs: dict[str, str] = field(default_factory=dict)


@dataclass
class RunResult:
    passed: bool
    iterations: list[Iteration] = field(default_factory=list)


def run_test(project_dir: Path, test_command: str) -> tuple[bool, str]:
    proc = subprocess.run(
        shlex.split(test_command),
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + "\n" + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def error_excerpt(output: str, max_lines: int = 40) -> str:
    lines = output.splitlines()
    return "\n".join(lines[-max_lines:])


def candidate_files(output: str, project_dir: Path, limit: int = 3) -> list[Path]:
    seen: list[Path] = []
    project_dir = project_dir.resolve()
    matches = _TRACE_FILE_RE.findall(output) + _PYTEST_FILE_RE.findall(output)
    for raw, _line in matches:
        p = Path(raw)
        if not p.is_absolute():
            p = (project_dir / p)
        try:
            p = p.resolve()
            p.relative_to(project_dir)
        except (ValueError, OSError):
            continue
        if p.is_file() and p not in seen:
            seen.append(p)
    return seen[-limit:]


def build_query(output: str) -> str:
    lines = [l.strip() for l in output.splitlines() if l.strip()]
    for line in reversed(lines):
        # Skip pytest's one-line summary (e.g. `FAILED test_app.py::... - Attr...`),
        # which truncates the message and carries the test id as search noise.
        if line.startswith(("FAILED", "ERROR ")) or "::" in line:
            continue
        # Strip pytest's `E   ` assertion marker so the query is the clean message.
        cleaned = re.sub(r"^E\s+", "", line)
        if re.search(r"(Error|Exception|Warning):", cleaned):
            return cleaned[:200]
    return lines[-1][:200] if lines else "python test failure"


# strict=False tolerates raw newlines/tabs inside string values, which LLMs
# routinely emit when returning multi-line file content.
_DECODER = json.JSONDecoder(strict=False)


def _demote_triple_quotes(text: str) -> str:
    """Some models wrap a multi-line file value in Python triple quotes instead
    of a JSON string, to avoid escaping the quotes inside it. The decoder is
    already lenient about literal newlines in strings, so demoting the
    triple-quote delimiter to a single double quote turns that back into
    parseable JSON. A no-op when the reply has no triple quotes."""
    return text.replace('"""', '"').replace("'''", '"')


def _parse_files(reply: str) -> tuple[str, dict[str, str]]:
    # Scan every "{" and return the first object that actually parses AND carries
    # a non-empty "files" dict. This skips braces inside any reasoning prose the
    # model emits before the JSON (a first-brace-to-last-brace slice would span
    # that and fail). We try the reply as-is first, then with Python triple-quote
    # file values demoted to JSON strings.
    base = _FENCE_RE.sub("", reply)
    for text in (base, _demote_triple_quotes(base)):
        for i, ch in enumerate(text):
            if ch != "{":
                continue
            try:
                data, _ = _DECODER.raw_decode(text[i:])
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and isinstance(data.get("files"), dict):
                files = {
                    k: v
                    for k, v in data["files"].items()
                    if isinstance(k, str) and isinstance(v, str)
                }
                if files:
                    return str(data.get("explanation", "")), files
    return "", {}


def _build_user_prompt(
    project_dir: Path, error: str, files: list[Path], hits: list[SearchHit]
) -> str:
    parts = ["## Failing test output\n", error, "\n"]
    parts.append("\n## Current project files\n")
    for f in files:
        rel = f.relative_to(project_dir.resolve())
        body = f.read_text(encoding="utf-8", errors="replace")[:6000]
        parts.append(f"\n### {rel}\n```\n{body}\n```\n")
    parts.append("\n## Live web search results\n")
    if hits:
        for h in hits:
            parts.append(f"\n- {h.title} ({h.url})\n{h.content}\n")
    else:
        parts.append("\n(no web results available)\n")
    return "".join(parts)


class LiveFixAgent:
    def __init__(self, config, project_dir: str | Path, test_command: str):
        self.config = config
        self.project_dir = Path(project_dir).resolve()
        self.test_command = test_command
        self.chat = NebiusChat(config)
        self.search = WebSearch(config.tavily_api_key)

    def _changes_something(self, files: dict[str, str]) -> bool:
        """True if at least one proposed file exists and differs from disk.

        A model will sometimes echo the file back unchanged or return a file it
        is not asked about; such a reply parses but fixes nothing. Treat it as a
        non-answer so the retry loop keeps looking instead of giving up.
        """
        for rel, content in files.items():
            target = (self.project_dir / rel).resolve()
            try:
                target.relative_to(self.project_dir)
            except ValueError:
                continue
            if target.exists() and content != target.read_text(
                encoding="utf-8", errors="replace"
            ):
                return True
        return False

    def _apply(self, files: dict[str, str]) -> tuple[list[str], dict[str, str]]:
        changed: list[str] = []
        diffs: dict[str, str] = {}
        for rel, content in files.items():
            target = (self.project_dir / rel).resolve()
            try:
                target.relative_to(self.project_dir)
            except ValueError:
                continue  # never write outside the project
            if not target.exists():
                continue  # only repair existing files
            before = target.read_text(encoding="utf-8", errors="replace")
            if content == before:
                continue  # no-op edit; do not count it as a change
            diffs[rel] = "".join(
                difflib.unified_diff(
                    before.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{rel}", tofile=f"b/{rel}",
                )
            )
            target.write_text(content, encoding="utf-8")
            changed.append(rel)
        return changed, diffs

    @traceable(name="livefix.run")
    def run(self, max_iters: int = 5) -> RunResult:
        result = RunResult(passed=False)
        for i in range(1, max_iters + 1):
            passed, output = run_test(self.project_dir, self.test_command)
            if passed:
                result.passed = True
                result.iterations.append(
                    Iteration(i, True, "", "", [], [], "test already passing")
                )
                return result

            error = error_excerpt(output)
            query = build_query(output)
            hits = self.search.search(query)
            files = candidate_files(output, self.project_dir)
            if not files:
                result.iterations.append(
                    Iteration(i, False, error, query, hits, [],
                              "no project file found in traceback"))
                break

            prompt = _build_user_prompt(self.project_dir, error, files, hits)
            # The model occasionally returns prose instead of the JSON contract;
            # retry a few times (temperature 0) before giving up on this iteration.
            explanation, proposed = "", {}
            # Escalate temperature on retry: a deterministic non-JSON or no-op
            # reply at temperature 0 would just repeat, so later attempts re-roll
            # it. Accept a reply only once it actually changes a project file; a
            # reply that parses but echoes the file back unchanged is not an answer.
            for temp in (0.0, 0.2, 0.4, 0.6, 0.8):
                try:
                    reply = self.chat.complete(_SYSTEM, prompt, temperature=temp)
                except Exception:
                    continue  # transient model/API failure: fall through to the next attempt
                explanation, proposed = _parse_files(reply)
                if proposed and self._changes_something(proposed):
                    break
                proposed = {}  # unusable (no JSON, or a no-op); keep trying
            changed, diffs = self._apply(proposed)
            result.iterations.append(
                Iteration(i, False, error, query, hits, changed, explanation, diffs))
            if not changed:
                break  # nothing applied; avoid a no-op loop

        passed, _ = run_test(self.project_dir, self.test_command)
        result.passed = passed
        return result
