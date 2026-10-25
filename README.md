# LiveFix

**A web-grounded agent that repairs broken code against moving APIs.**

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/).
Runs on **Nebius Token Factory** with an **NVIDIA Nemotron** open model, grounded by
**Tavily** live web search.

## The problem

Most "AI fixes my code" tools fail on the breakages that matter most: the ones
that happened *after* the model's training cutoff. A dependency drops a function,
a framework renames an argument, a cloud SDK changes its auth flow. The model has
never seen the new API, so it confidently writes the old one back.

## How LiveFix solves it

LiveFix closes that gap by putting the live web in the loop:

1. **Run** the failing test and capture the traceback.
2. **Locate** the project file named in the traceback (with a path-escape guard,
   so it never touches files outside the project).
3. **Search** the web with Tavily for the current migration or fix, using the
   exception line as the query. This is the step a plain LLM cannot do.
4. **Repair**: hand the traceback, the current file contents, and the web
   excerpts to Nemotron on Nebius Token Factory, and ask for the complete new
   file content.
5. **Re-run** the test. Loop until it passes or the budget is spent.

The web excerpts are what let Nemotron apply a fix it was never trained on.

## Why this is a good use of Tavily

The repair is only as current as the search. Tavily's `search_depth="advanced"`
pulls the up-to-date docs, changelogs, and migration notes that pin the exact
replacement API, so the model's edit is grounded in today's reality instead of
its training-time memory. Turn the search off and LiveFix degrades to a
guess-from-memory patcher; turn it on and it fixes post-cutoff breakages.

## Does the web search actually help? (benchmark)

That last claim is measurable, so we measure it. [`benchmark/`](benchmark/) holds
five cases, each a failing test caused by a real, documented API change that
post-dates common model cutoffs (`np.float` removed in NumPy 1.24,
`DataFrame.append` in pandas 2.0, `BaseSettings` moved in Pydantic v2,
`Markup` removed from `flask` in 3.1, `collections.Mapping` in Python 3.10). The
harness runs the identical loop with Tavily ON and OFF and reports the repair
rate for each. The gap is the value the web grounding adds.

```bash
pip install -r requirements.txt -r benchmark/requirements.txt
python benchmark/run_benchmark.py --self-test   # validate the harness offline, no keys
python benchmark/run_benchmark.py --repeats 3   # the real measurement
```

See [benchmark/README.md](benchmark/README.md) for the method and how to read the
result.

## Quick start

```bash
pip install -r requirements.txt

cp .env.example .env        # fill in NEBIUS_API_KEY and TAVILY_API_KEY
set -a; . ./.env; set +a    # load them into the environment

# Repair the bundled broken example (uses a removed stdlib import):
python -m livefix --project examples/broken_project --test "python -m pytest -q"
```

Expected: LiveFix finds `from collections import Mapping` (removed in Python
3.10), searches for the current import, rewrites it to
`from collections.abc import Mapping`, and the test turns green.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `NEBIUS_API_KEY` | Token Factory bearer key | (required) |
| `NEBIUS_BASE_URL` | OpenAI-compatible endpoint | `https://api.tokenfactory.nebius.com/v1/` |
| `NEBIUS_MODEL` | NVIDIA open model id | `nvidia/nemotron-3-super-120b-a12b` |
| `TAVILY_API_KEY` | Live web search | (optional; off when unset) |
| `LANGSMITH_TRACING` | Turn LangSmith tracing on | (optional; off when unset) |
| `LANGSMITH_API_KEY` | LangSmith key (needed with the flag) | (optional) |

Some Nebius regions use a region-suffixed host; confirm the exact base URL in
your dashboard when you create the key.

## Tracing (LangSmith, optional)

Each run is a loop of a Tavily search and a Nemotron completion per iteration, so
when a repair goes wrong you want to see those steps. Set `LANGSMITH_TRACING=true`
and `LANGSMITH_API_KEY=...` and every run, model call, and search call is traced
to LangSmith under the `LANGSMITH_PROJECT` project. With the flag or key unset,
tracing is a transparent no-op and LangSmith is not even imported, so LiveFix has
no hard dependency on it.

## Tests

```bash
python -m pytest tests/ -q
```

The tests stub the Nebius and Tavily SDKs, so they run with no keys and no
network.

## License

MIT. See [LICENSE](LICENSE).
