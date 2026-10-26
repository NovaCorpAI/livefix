"""The repair parser must survive a model that wraps file contents in Python
triple quotes instead of a JSON string (observed with Nemotron)."""
from livefix.agent import _parse_files


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
