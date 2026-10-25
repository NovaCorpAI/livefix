"""LiveFix web UI: run the repair agent on a demo case and return the full trace.

Each run happens on a throwaway copy of the case, so the bundled examples stay in
their original broken state. The frontend animates the trace red -> green.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, Response, jsonify, send_from_directory

from livefix.agent import LiveFixAgent
from livefix.config import Config

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"
STATIC = Path(__file__).resolve().parent / "static"


def _load_dotenv() -> None:
    """Minimal .env loader so `python webapp/server.py` works without a shell."""
    env = REPO / ".env"
    if not env.is_file():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip())


def list_cases() -> list[dict]:
    cases = []
    if EXAMPLES.is_dir():
        for d in sorted(EXAMPLES.iterdir()):
            meta = d / "livefix_case.json"
            if meta.is_file():
                m = json.loads(meta.read_text(encoding="utf-8"))
                cases.append({"id": d.name, **m})
    return cases


app = Flask(__name__)


@app.get("/")
def index() -> Response:
    return send_from_directory(STATIC, "index.html")


@app.get("/api/cases")
def cases() -> Response:
    return jsonify(list_cases())


@app.post("/api/run/<case_id>")
def run(case_id: str) -> Response:
    src = EXAMPLES / case_id
    meta_path = src / "livefix_case.json"
    if not meta_path.is_file():
        return jsonify({"error": f"unknown case: {case_id}"}), 404
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / case_id
        shutil.copytree(src, work, ignore=shutil.ignore_patterns("livefix_case.json"))
        try:
            cfg = Config.from_env()
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 400
        agent = LiveFixAgent(cfg, work, meta["test_command"])
        t0 = time.time()
        res = agent.run(max_iters=int(meta.get("max_iters", 4)))
        elapsed = round(time.time() - t0, 1)

    iterations = [
        {
            "index": it.index,
            "passed": it.passed,
            "error": (it.query or it.error_excerpt or "").strip(),
            "hits": [{"title": h.title, "url": h.url} for h in it.hits],
            "changed": it.changed,
            "explanation": it.explanation,
            "diffs": it.diffs,
        }
        for it in res.iterations
    ]
    return jsonify(
        {
            "case": case_id,
            "title": meta.get("title", case_id),
            "model": cfg.nebius_model,
            "web_search": agent.search.enabled,
            "test_command": meta["test_command"],
            "passed": res.passed,
            "elapsed": elapsed,
            "iterations": iterations,
        }
    )


if __name__ == "__main__":
    _load_dotenv()
    port = int(os.environ.get("PORT", "5050"))
    print(f"LiveFix web UI on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, threaded=True)
