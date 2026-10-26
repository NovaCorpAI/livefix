"""The repair parser must survive a model that wraps file contents in Python
triple quotes instead of a JSON string (observed with Nemotron)."""
import shutil
from pathlib import Path

import pytest

from livefix.agent import (
    _is_test_file,
    _looks_double_escaped,
    _parse_files,
    _recover_double_encoded,
    _valid_js,
    _valid_python,
    candidate_files,
)
from livefix.remediate import bump_package_json, bump_pin


def test_valid_python_accepts_good_file():
    assert _valid_python({"a.py": "def f():\n    return 1\n"})


def test_valid_python_rejects_broken_docstring():
    # A real failure mode: an unterminated triple-quoted string.
    assert not _valid_python({"a.py": '"""doc\nfrom x import y\n""\nz = 1\n'})


def test_valid_python_ignores_non_python():
    assert _valid_python({"requirements.txt": "pillow>=13.0.0\n"})


def test_parse_triple_quoted_file_value():
    # A real Nemotron shape: a valid JSON envelope whose file value is delimited
    # with Python triple quotes (invalid JSON on its own).
    reply = (
        '{\n'
        '  "explanation": "swap the removed API",\n'
        '  "files": {\n'
        '    "app.py": """from PIL import ImageCms\n'
        '\n'
        'def f(p):\n'
        '    return ImageCms.getProfileName(p).strip()\n'
        '"""\n'
        '  }\n'
        '}'
    )
    expl, files = _parse_files(reply)
    assert "app.py" in files
    assert "getProfileName" in files["app.py"]
    assert expl


def test_parse_standard_json_still_works():
    reply = '{"explanation":"y","files":{"a.py":"print(1)\\n"}}'
    expl, files = _parse_files(reply)
    assert files["a.py"] == "print(1)\n"
    assert expl == "y"


def test_parse_rejects_object_without_files():
    expl, files = _parse_files('{"explanation":"nothing","files":{}}')
    assert files == {}


# --- cross-ecosystem (JavaScript / npm) repair support ---

def test_is_test_file_matches_conventions():
    for p in ("test/filelist.test.js", "tests/foo.py", "test_app.py",
              "app_test.py", "conftest.py", "pkg/foo.spec.ts"):
        assert _is_test_file(p), p


def test_is_test_file_leaves_source_alone():
    for p in ("filelist.js", "app.py", "colorprofile/name.py", "src/util.ts"):
        assert not _is_test_file(p), p


def test_candidate_files_parses_js_stack_trace(tmp_path):
    # A real node --test stack: a parenthesized frame and a bare frame, with a
    # path that contains spaces and a Windows drive colon.
    (tmp_path / "filelist.js").write_text("module.exports = {};\n", encoding="utf-8")
    base = str(tmp_path / "filelist.js")
    output = (
        "  TypeError: glob is not a function\n"
        f"      at {base}:16:5\n"
        f"      at listMatches ({base}:15:10)\n"
    )
    files = candidate_files(output, tmp_path)
    assert (tmp_path / "filelist.js").resolve() in files


def test_looks_double_escaped_detects_single_line_literal_bodies():
    # The decoded body is one physical line of literal backslash-n, no real
    # newline: a double-encoded reply that would apply as an inert string.
    body = ('"use strict\\n\\nconst { glob } = require(\\"glob\\");\\n'
            'function f(p){ return glob(p); }\\nmodule.exports = { f };"')
    assert _looks_double_escaped(body)
    # Real multi-line code is left alone.
    assert not _looks_double_escaped(
        'const { glob } = require("glob");\nmodule.exports = {};\n')


def test_recover_double_encoded_restores_real_source():
    body = ('"use strict\\n\\nconst { glob } = require(\\"glob\\");\\n'
            'module.exports = { glob };"')
    out = _recover_double_encoded(body)
    assert out.startswith('use strict\n\n')
    assert 'require("glob")' in out
    assert "\\n" not in out  # literal escapes are gone


def test_parse_files_recovers_double_encoded_value():
    # A valid JSON envelope whose file value is itself a quoted, escaped string
    # (the model double-encoded the body). _parse_files recovers real source.
    reply = (
        '{"explanation":"fix","files":{"a.js":'
        '"\\"const { glob } = require(\\\\\\"glob\\\\\\");\\\\nmodule.exports = { glob };\\""}}'
    )
    _expl, files = _parse_files(reply)
    assert "a.js" in files
    assert "\n" in files["a.js"]  # recovered to real newlines
    assert 'require("glob")' in files["a.js"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_valid_js_accepts_good_and_rejects_broken():
    assert _valid_js({"a.js": 'const x = 1;\nmodule.exports = { x };\n'})
    assert not _valid_js({"a.js": 'const x = (;\n'})


def test_valid_js_ignores_non_js():
    assert _valid_js({"requirements.txt": "glob\n"})


# --- npm manifest bump ---

def test_bump_package_json_edits_dependency(tmp_path):
    mani = tmp_path / "package.json"
    mani.write_text(
        '{\n  "name": "x",\n  "dependencies": {\n    "glob": "^7.2.3"\n  }\n}\n',
        encoding="utf-8")
    old, new = bump_package_json(mani, "glob", "10.4.5")
    assert old == '"glob": "^7.2.3"'
    assert new == '"glob": ">=10.4.5"'
    import json as _json
    data = _json.loads(mani.read_text(encoding="utf-8"))
    assert data["dependencies"]["glob"] == ">=10.4.5"
    assert data["name"] == "x"  # other keys preserved


def test_bump_package_json_missing_package(tmp_path):
    mani = tmp_path / "package.json"
    mani.write_text('{"dependencies": {"left-pad": "1.0.0"}}', encoding="utf-8")
    assert bump_package_json(mani, "glob", "10.4.5") == (None, None)


def test_bump_pin_dispatches_to_json(tmp_path):
    mani = tmp_path / "package.json"
    mani.write_text('{"devDependencies": {"glob": "7"}}', encoding="utf-8")
    old, new = bump_pin(mani, "glob", "10.4.5")
    assert old == '"glob": "7"' and new == '"glob": ">=10.4.5"'


def test_bump_pin_still_handles_requirements(tmp_path):
    mani = tmp_path / "requirements.txt"
    mani.write_text("pillow==12.3.0\n", encoding="utf-8")
    old, new = bump_pin(mani, "pillow", "13.0.0")
    assert "pillow" in (new or "") and ">=13.0.0" in (new or "")
