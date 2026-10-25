# LiveFix demo video script (target 2:30, hard cap 3:00)

Judging rewards a clear problem, a visible live fix, and proof it generalizes.
This script hits all three. Record the terminal at a readable font size; keep the
camera on the screen, voice over the top.

## Shot 0 — Title card (0:00 to 0:08)

On screen: "LiveFix: repair broken code against moving APIs. Nebius Token Factory
+ NVIDIA Nemotron + Tavily."

Say: "LiveFix fixes the bugs other AI tools can't: the ones caused by API changes
that happened after the model was trained."

## Shot 1 — The problem (0:08 to 0:35)

On screen: open `examples/broken_project/app.py`, highlight
`from collections import Mapping`. Then run the test and let it fail:

```bash
python -m pytest -q
```

Say: "This import was removed in Python 3.10. A model trained before that change
will happily write it back, because to the model it was never wrong. Watch the
test fail at import."

## Shot 2 — The live fix (0:35 to 1:35)

Run LiveFix:

```bash
python -m livefix --project examples/broken_project --test "python -m pytest -q"
```

As it runs, narrate the loop over what prints:

- "It runs the failing test and reads the traceback."
- "It searches the live web with Tavily for the current fix. This is the step a
  plain model can't take."
- "It sends the traceback, the file, and those web results to NVIDIA Nemotron on
  Nebius Token Factory, and gets back the corrected file."
- "It re-runs the test."

End on the green result line: "RESULT: test passes. LiveFix repaired the
project." Show the one-line diff: `collections` to `collections.abc`.

Say: "No human in the loop. The fix came from today's web, not the model's
memory."

## Shot 3 — Proof it generalizes (1:35 to 2:10)

On screen: `benchmark/README.md` table of the five cases, then run:

```bash
python benchmark/run_benchmark.py --self-test
```

Say: "One example is a demo; five is a claim. We built a benchmark of real,
documented, post-cutoff breakages across NumPy, pandas, Pydantic, Flask, and the
standard library. It runs the same loop with web search on and off, and reports
the repair rate for each. The gap is what Tavily buys you. This self-test proves
the harness measures honestly, offline, before spending a token."

(If credits are live at record time, show the real ON vs OFF table instead.)

## Shot 4 — Built on the stack, and feedback (2:10 to 2:30)

On screen: the Nebius "Start building" snippet, then `FEEDBACK.md`.

Say: "It's a small codebase because Nebius Token Factory is OpenAI-compatible, so
the official SDK just worked. Optional LangSmith tracing shows every step. And we
wrote up concrete platform feedback from actually building this. LiveFix: as
current as the web, grounded by Tavily, powered by NVIDIA Nemotron on Nebius."

## Recording checklist

- Terminal font large enough to read on a phone.
- Pre-install deps so there is no pip wait on camera.
- Have `.env` loaded before recording (keys off screen).
- One clean take of Shot 2; if the live run is slow, speed the middle up in edit
  but keep the start, the search line, and the green result at real speed.
- Keep total under 3:00.
