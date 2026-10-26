"""Network-free, key-free tests for the remediation helpers."""

from pathlib import Path

from livefix.remediate import bump_pin, _parse_json


def test_bump_pin_rewrites_exact_pin(tmp_path: Path):
    req = tmp_path / "requirements.txt"
    req.write_text("pillow==12.3.0\nrequests>=2\n", encoding="utf-8")
    old, new = bump_pin(req, "pillow", "13.0.0")
    assert old == "pillow==12.3.0"
    assert new == "pillow>=13.0.0"
    assert "pillow>=13.0.0" in req.read_text(encoding="utf-8")
    assert "requests>=2" in req.read_text(encoding="utf-8")  # untouched


def test_bump_pin_is_case_insensitive_and_keeps_comment(tmp_path: Path):
    req = tmp_path / "requirements.txt"
    req.write_text("Pillow==12.3.0  # icc profiles\n", encoding="utf-8")
    old, new = bump_pin(req, "pillow", "13.0.0")
    assert new == "pillow>=13.0.0  # icc profiles"


def test_bump_pin_absent_package_is_noop(tmp_path: Path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests>=2\n", encoding="utf-8")
    assert bump_pin(req, "pillow", "13.0.0") == (None, None)
    assert req.read_text(encoding="utf-8") == "requests>=2\n"  # unchanged


def test_parse_json_finds_first_object():
    assert _parse_json('noise {"safe_version": "13.0.0"} tail')["safe_version"] == "13.0.0"
    assert _parse_json("no json") == {}
