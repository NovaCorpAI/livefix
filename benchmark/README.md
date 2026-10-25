# LiveFix benchmark: what does live web search buy you?

LiveFix repairs a failing test by grounding an NVIDIA Nemotron model (on Nebius
Token Factory) with live web search (Tavily). This benchmark measures the one
thing that claim rests on: **how much the web grounding actually changes the
repair rate.**

## The idea

Every case is a tiny project with a failing test caused by a **real, documented
breaking change that post-dates common model training cutoffs**: an import or API
that a library removed, where the fix is written down online but unlikely to be
reliably in the weights. For each case the harness runs the exact same loop twice:

| condition | model | prompts | web results |
|---|---|---|---|
| web **ON**  | Nemotron | identical | Tavily, live |
| web **OFF** | Nemotron | identical | none |

Everything but the web results is held constant, so the gap between the two
columns is the value Tavily adds.

## The cases

| folder | library | breaking change | removed in |
|---|---|---|---|
| `py310_collections` | stdlib | `from collections import Mapping` | Python 3.10 (2021) |
| `numpy_aliases` | numpy | `np.float` alias | NumPy 1.24 (2022) |
| `pandas_append` | pandas | `DataFrame.append` | pandas 2.0 (2023) |
| `pydantic_settings` | pydantic | `BaseSettings` moved out of `pydantic` | Pydantic v2 (2023) |
| `flask_markup` | flask | `from flask import Markup` | Flask 3.1 (2024) |

Each folder has the broken `app.py`, a `test_app.py`, a `livefix_case.json`
(metadata the harness reads), and a `FIX.md` documenting the root cause, the
minimal fix, and why web grounding helps.

## Running it

```bash
# 1. Install the repo deps and the per-case libraries (at versions that removed
#    the old API).
pip install -r requirements.txt -r benchmark/requirements.txt

# 2. Set keys. Web-ON needs Tavily; both need Nebius.
export NEBIUS_API_KEY=...       # on Windows PowerShell: $env:NEBIUS_API_KEY="..."
export TAVILY_API_KEY=...

# 3. Run. Default is all cases, one run per condition.
python benchmark/run_benchmark.py
python benchmark/run_benchmark.py --repeats 3
python benchmark/run_benchmark.py --cases numpy_aliases pandas_append
```

The harness copies each case to a fresh temp dir per run (the agent edits files
in place), confirms the case really starts red, runs the repair, and prints a
pass/total table. Results are also written to `benchmark/results/<timestamp>.json`
and `benchmark/results/latest.md`.

## Trusting the harness before paying for a run

```bash
python benchmark/run_benchmark.py --self-test
```

This validates the whole measurement path (copy-to-temp, the red check, the loop,
JSON parsing, file apply, re-run) on the stdlib case with a **stubbed model and no
network**, so you can confirm the harness is sound before spending any tokens. It
prints `-> OK` on success.

## Reading the result

A healthy result looks like a clear ON-over-OFF gap: the web-ON column repairs
cases the web-OFF column cannot, because the fix is documentation the model did
not have. A case that passes in both columns is one the model already knew (fine,
but it is not evidence for web grounding); a case that fails in both is a prompt
or model-capability limit, not a search limit. The headline number is the overall
repair rate, ON vs OFF.
