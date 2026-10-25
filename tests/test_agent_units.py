"""Network-free, key-free tests for the agent's pure helpers."""

from pathlib import Path

from livefix.agent import (
    build_query,
    candidate_files,
    error_excerpt,
    _parse_files,
)

REPO = Path(__file__).resolve().parent.parent
EXAMPLE = REPO / "examples" / "broken_project"


def test_build_query_picks_exception_line():
    out = (
        "Traceback (most recent call last):\n"
        '  File "app.py", line 7\n'
        "ImportError: cannot import name 'Mapping' from 'collections'"
    )
    q = build_query(out)
    assert "ImportError" in q and "Mapping" in q


def test_candidate_files_resolves_in_project():
    tb = f'  File "{EXAMPLE / "app.py"}", line 7, in <module>\n'
    assert [p.name for p in candidate_files(tb, EXAMPLE)] == ["app.py"]


def test_candidate_files_rejects_paths_outside_project():
    tb = '  File "C:/Windows/system32/evil.py", line 1, in <module>\n'
    assert candidate_files(tb, EXAMPLE) == []


def test_parse_files_tolerates_fences_and_raw_newlines():
    reply = (
        "Sure!\n```json\n"
        '{"explanation":"use abc","files":{"app.py":"from collections.abc import Mapping\n"}}'
        "\n```"
    )
    expl, files = _parse_files(reply)
    assert expl == "use abc"
    assert files == {"app.py": "from collections.abc import Mapping\n"}


def test_parse_files_returns_empty_on_garbage():
    assert _parse_files("no json here at all") == ("", {})


def test_error_excerpt_keeps_tail():
    assert error_excerpt("a\nb\nc\nd", max_lines=2) == "c\nd"


def test_candidate_files_parses_pytest_collection_format():
    # pytest renders frames as `<path>:<line>: in <func>` (not the File "..." form).
    app = EXAMPLE / "app.py"
    lines = [
        "test_app.py:1: in <module>",
        "    from app import count_keys",
        f"{app}:8: in <module>",
        "    from collections import Mapping",
        "E   ImportError: cannot import name 'Mapping' from 'collections'",
    ]
    out = chr(10).join(lines)
    names = [p.name for p in candidate_files(out, EXAMPLE)]
    assert "app.py" in names
