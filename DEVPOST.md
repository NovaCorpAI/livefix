# LiveFix (Devpost submission copy)

> A web-grounded agent that repairs broken code against moving APIs. Runs on
> Nebius Token Factory with an NVIDIA Nemotron open model, grounded by Tavily
> live web search.

## Inspiration

Every "AI fixes my code" tool shares one blind spot: the breakages that matter
most are the ones that happened **after** the model's training cutoff. A library
drops a function, a framework renames an import, an SDK changes its auth. The
model never saw the new API, so it confidently writes the old one back, and your
test stays red. We wanted an agent whose fixes are as current as the web, not as
old as the weights.

## What it does

LiveFix takes a project with a failing test and repairs it in a loop:

1. Runs the test and captures the traceback.
2. Locates the project file named in the traceback (with a path-escape guard, so
   it never writes outside the project).
3. Searches the live web with Tavily for the current fix, using the exception
   line as the query. This is the step a plain LLM cannot do.
4. Hands the traceback, the current file, and the web excerpts to NVIDIA Nemotron
   on Nebius Token Factory, and asks for the complete new file.
5. Re-runs the test, and loops until it passes or the budget is spent.

The web excerpts are what let the model apply a fix it was never trained on.

## How we built it

- **Model:** `nvidia/nemotron-3-super-120b-a12b` on **Nebius Token Factory**,
  through the OpenAI-compatible endpoint, so the official `openai` SDK worked
  unchanged against Nebius with just a base URL and key.
- **Grounding:** **Tavily** `search_depth="advanced"` for current docs,
  changelogs, and migration notes.
- **Agent:** a small, dependency-light Python package (`livefix/`): a test
  runner, a traceback-to-file resolver, a brace-scanning JSON parser with a
  temperature-escalating retry, and the repair loop.
- **Observability:** optional **LangSmith** tracing on the loop, the model call,
  and the search call, as a transparent no-op when unconfigured.
- **Demo surface:** a Flask app and a hosted static page on **Vercel** that
  replays a real recorded run.

## How we proved it works

We did not want to just assert that web search helps, so we built a benchmark
(`benchmark/`) of five cases, each a real, documented, post-cutoff API change:
`collections.Mapping` (Python 3.10), `np.float` (NumPy 1.24), `DataFrame.append`
(pandas 2.0), `BaseSettings` moving to `pydantic-settings` (Pydantic v2), and
`Markup` removed from `flask` (3.1). The harness runs the identical loop with
Tavily ON and OFF and reports the repair rate for each. It also ships a
`--self-test` that validates the whole measurement path offline with a stubbed
model, so the harness is trustworthy before a single paid token is spent.

## Challenges we ran into

- **Guaranteed JSON.** The model occasionally wrapped its JSON answer in prose or
  a fence. We added a parser that scans for the first object carrying a `files`
  key and a retry that escalates temperature. (Written up in `FEEDBACK.md` as our
  top platform ask: a native JSON-output mode.)
- **Safety of file writes.** An agent that rewrites files must never escape the
  project; every target path is resolved and checked before any write.
- **Honest demo without leaking keys.** The public page replays a real captured
  run rather than exposing live API keys, and says so.

## Accomplishments we are proud of

- A working, safe repair loop in a small, readable codebase.
- A real benchmark that turns the core claim into a number, with an offline
  self-test so anyone can trust it.
- Concrete, actionable platform feedback from genuinely building on the stack.

## What we learned

The OpenAI-compatible endpoint makes Nebius trivial to adopt from existing code,
and Nemotron produces correct minimal patches when it is grounded well. The
leverage is almost entirely in the grounding: the same model with and without
live search is close to two different tools.

## What's next

- Run the benchmark at scale once program credits land, and publish the ON vs OFF
  numbers.
- A LangSmith evaluation that scores repairs across the dataset automatically.
- More languages and test runners (currently Python and pytest), and a GitHub
  Action that opens a fix PR on a red CI run.

## Built with

Python, Nebius Token Factory, NVIDIA Nemotron, Tavily, LangSmith, OpenAI SDK,
pytest, Flask, Vercel.
