# LiveFix demo video script (target 2:30, hard cap 3:00)

Judging rewards a clear problem, a visible live result, and proof it generalizes.
This script hits all three around the security-remediation story. Record the
terminal at a readable font size; voice over the top.

## Shot 0: Title card (0:00 to 0:08)

On screen: "LiveFix: the security upgrade that fixes the CVE and keeps your build
green. Nebius Token Factory + NVIDIA Nemotron + Tavily."

Say: "A scanner flags a CVE in a dependency. The bump PR breaks your build and
rots. LiveFix closes that loop, autonomously."

## Shot 1: The problem (0:08 to 0:40)

On screen: open `examples/vulnerable_project/requirements.txt` (`pillow==12.3.0`,
flagged for CVE-2026-112398) and `app.py` (uses `profile.product_name`). Run the
test and let it fail:

```bash
python -m pytest -q
```

Say: "This project pins a Pillow with a critical RCE. The fix only ships in Pillow
13, and that release removed the API this code uses. So the security upgrade
itself turns the build red. That is two problems: which version is safe, and how
to not break the code."

## Shot 2: The live remediation (0:40 to 1:45)

Run LiveFix end to end:

```bash
python -m livefix.remediate --project examples/vulnerable_project \
  --package pillow --advisory CVE-2026-112398 --test "python -m pytest -q"
```

Narrate over the three steps as they print:

- "Step one: it searches the live web with Tavily and resolves the safe version,
  Pillow 13.0.0. A plain model can't know this: the CVE is days old, newer than
  its training. Watch the source: it's the real advisory."
- "Step two: it bumps the pin, 12.3.0 to 13.0.0."
- "Step three: it runs the test, sees the upgrade broke `product_name`, and has
  NVIDIA Nemotron on Nebius rewrite it to the current API, `getProfileName`."

End on: "RESULT: CVE-2026-112398 remediated. Pin bumped and tests pass." Show the
two diffs (requirements and app.py).

Say: "No human in the loop. A merge-ready fix, not a red bump PR."

## Shot 3: Proof, and honesty (1:45 to 2:20)

On screen: run the security benchmark (or show `benchmark/security/results/latest.md`):

```bash
python benchmark/security/run_security_benchmark.py --repeats 3
```

Say: "One fix is a demo. We measured it on five real 2026 CVEs across two
ecosystems, PyPI and npm, same model, web on versus off. Fifteen out of fifteen
remediated with Tavily, zero out of fifteen without, and without the web the model
doesn't guess, it abstains. That gap is the value of live search, and it's
impossible to fake. We're also honest about the limit: for old, well-known API
breaks the model needs no web. The web earns its place on the fact it can't know:
the fresh CVE's safe version."

## Shot 4: Built on the stack, and feedback (2:20 to 2:40)

On screen: the Nebius "Start building" snippet, then `FEEDBACK.md`, then the live
page https://livefix.novacorplabs.com.

Say: "Small codebase, because Nebius Token Factory is OpenAI-compatible, so the
official SDK just worked. Optional LangSmith tracing shows every step. We wrote up
concrete platform feedback from building this."

Optional closing beat (show PR #1 and PR #2 on the repo): "And it ships as a
GitHub Action, so a scanner alert opens this as a signed, verified PR: a one-line
summary, the trace, and a check that is green only because the tests pass. Here
are two it opened for real, and the second one is the proof it generalizes: the
upgrade broke three files, and LiveFix repaired each until the whole build went
green. LiveFix: live-grounded security remediation, on NVIDIA Nemotron and Nebius,
with Tavily."

## Recording checklist

- Terminal font large enough to read on a phone.
- Pre-install deps and Pillow 13 so there is no pip wait on camera.
- Have `.env` loaded before recording (keys off screen).
- One clean take of Shot 2; if the live run is slow, speed the middle up in edit
  but keep the resolved-version line, the Tavily source, and the green result at
  real speed.
- `git checkout examples/vulnerable_project` to reset between takes.
- Keep total under 3:00.
