# Broken example project

`app.py` uses `from collections import Mapping`, which Python 3.10 removed.
Running the test fails at import:

    $ python -m pytest -q
    ImportError: cannot import name 'Mapping' from 'collections'

Repair it with LiveFix from the repo root:

    python -m livefix --project examples/broken_project --test "python -m pytest -q"

LiveFix reads the traceback, searches the web for the current import, asks the
Nemotron model to rewrite `app.py`, and re-runs the test until it passes. The
fix is `from collections.abc import Mapping`.
