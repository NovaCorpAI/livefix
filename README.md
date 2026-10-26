# LiveFix

**An autonomous agent that remediates a vulnerable dependency end to end: it
resolves the safe version from the live web, bumps the pin, and repairs the code
the upgrade breaks, verified by your tests.**

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/).
Runs on **Nebius Token Factory** with an **NVIDIA Nemotron** open model, grounded
by **Tavily** live web search. Live demo: <https://livefix.novacorplabs.com>.

## The problem: a security bump is two walls, not one

A scanner tells you a dependency has a CVE. Dependabot and friends open a
version-bump PR and stop. Two walls keep that PR from ever turning green:

1. **The fact.** Which version is even safe? A CVE disclosed this month
   post-dates every model's training cutoff, so a plain model cannot know the
   fixed version. The honest ones say so; the rest guess.
2. **The break.** The safe version is often a major release that removed an API
   you used, so the upgrade that closes the CVE turns your tests red, and the PR
   rots unmerged.

LiveFix is the piece that closes both.

## How it works

```
python -m livefix.remediate \
  --project examples/vulnerable_project \
  --package pillow --advisory CVE-2026-112398 \
  --test "python -m pytest -q"
```

1. **Resolve** (Tavily): search the live web for the advisory and read off the
   minimal safe version. This is the fact the weights cannot hold.
2. **Bump**: pin the dependency to that version in the manifest.
3. **Repair** (Nemotron on Nebius): run the LiveFix repair loop to rewrite
   whatever the upgrade broke, grounded in the current docs.
4. **Verify**: re-run the project's own tests, looping until green or the budget
   is spent. A path-escape guard keeps every write inside the project.

The result is a green, merge-ready change instead of a red bump PR.

## Why this is a good use of Tavily

The load-bearing step is the one a model provably cannot do from memory: name the
safe version for a freshly disclosed CVE. We measured it. [`benchmark/security/`](benchmark/security/)
gives the same Nemotron model five real, 2026-disclosed CVEs, across two
ecosystems (PyPI and npm), and asks for the minimal safe version, with the live
web on and off. Identical model, identical prompt, one switch:

| Advisory (2026) | Package | Ecosystem | Web ON | Web OFF |
| --- | --- | --- | --- | --- |
| CVE-2026-112398 (critical RCE) | pillow | PyPI | 3/3 | 0/3 (abstained) |
| CVE-2026-111497 (Brotli decoder RCE) | brotli | PyPI | 3/3 | 0/3 (abstained) |
| CVE-2026-42309 (heap overflow) | pillow | PyPI | 3/3 | 0/3 (abstained) |
| CVE-2026-97689 (chunk-size buffering) | urllib3 | PyPI | 3/3 | 0/3 (abstained) |
| CVE-2026-59873 (decompression DoS) | tar | npm | 3/3 | 0/3 (abstained) |

Without the web the model does not hallucinate a version, it **abstains**: it
knows it cannot know. Tavily fills exactly that gap.

Every CVE above is real and checkable. [`benchmark/security/GROUND_TRUTH.md`](benchmark/security/GROUND_TRUTH.md)
links each one to NVD, OSV and the GitHub Advisory Database, and every safe
version we grade against matches the authoritative fixed version there.

```bash
python benchmark/security/run_security_benchmark.py --repeats 3
```

## An honest note on where the web helps

We only claim the web where it earns its place. We also measured the *code* repair
step on its own ([`benchmark/`](benchmark/), five pre-cutoff breakages like
`np.float` and `DataFrame.append`), and a strong model repairs those with or
without search, because it already knows those APIs. So the web's decisive,
un-fakeable contribution is the post-cutoff **fact** (the safe version, the fresh
advisory), not out-reasoning the model on code it already understands. The repair
loop still benefits from current docs on genuinely novel breakages, and it is
what turns the security bump green, but we do not overclaim it.

```bash
pip install -r requirements.txt -r benchmark/requirements.txt
python benchmark/run_benchmark.py --self-test   # validate the harness offline, no keys
python benchmark/run_benchmark.py --repeats 3   # the code-repair measurement
```

## Repair-only mode

The repair loop also runs on its own, for any failing test (no CVE required):

```bash
python -m livefix --project examples/broken_project --test "python -m pytest -q"
```

## Quick start

```bash
pip install -r requirements.txt

cp .env.example .env        # fill in NEBIUS_API_KEY and TAVILY_API_KEY
set -a; . ./.env; set +a    # load them into the environment

# Remediate the bundled vulnerable example (CVE-2026-112398 in a pinned Pillow):
python -m livefix.remediate --project examples/vulnerable_project \
  --package pillow --advisory CVE-2026-112398 --test "python -m pytest -q"
```

Expected: LiveFix resolves Pillow's safe version (13.0.0) from the live web,
bumps `pillow==12.3.0` to `pillow>=13.0.0`, and repairs the code the upgrade
broke (`ImageCmsProfile.product_name`, removed in Pillow 13, becomes
`ImageCms.getProfileName`), and the test turns green.

## Run it as a GitHub Action

LiveFix ships as a reusable action (`action.yml`), so a scanner alert can open a
verified remediation PR with no human in the loop:

```yaml
- uses: novacorp-labs/livefix@v1
  env:
    NEBIUS_API_KEY: ${{ secrets.NEBIUS_API_KEY }}
    TAVILY_API_KEY: ${{ secrets.TAVILY_API_KEY }}
  with:
    package: pillow
    advisory: CVE-2026-112398
    test: python -m pytest -q
    extra-deps: pytest   # your project's test runner, installed on the runner
```

The PR it opens carries an honest signature: a one-line summary, a collapsed
"what LiveFix did" block (the resolved version and its source, the bump, the
repair, and the LangSmith trace), a machine-readable commit trailer, and a
`LiveFix / remediation-verified` check that goes green only when the project's
tests pass. It says the change was *remediated and verified by tests*, never that
a human reviewed it. A rendered example is in
[`examples/sample_remediation_pr.md`](examples/sample_remediation_pr.md), and a
full workflow in [`.github/workflows/livefix-remediate.yml`](.github/workflows/livefix-remediate.yml).

## Connect your credentials

LiveFix uses two services you bring yourself, both with a free tier. You never
hand your keys to us; they stay in your own environment.

1. **Nebius Token Factory** (serves the model): create a key in the Nebius AI
   Studio / Token Factory dashboard. It becomes `NEBIUS_API_KEY`.
2. **Tavily** (live web search): create a key at <https://tavily.com>. It becomes
   `TAVILY_API_KEY`.

**For the CLI**, put them in a local `.env` (it is git-ignored, never committed):

```
NEBIUS_API_KEY=...
TAVILY_API_KEY=...
```

**For the GitHub Action**, add them as encrypted repository secrets (Settings >
Secrets and variables > Actions > New repository secret), named `NEBIUS_API_KEY`
and `TAVILY_API_KEY`. Secrets are never stored in the code, are masked in the
logs, and GitHub does not expose them to pull requests opened from forks, so
browsing the repo never reveals them.

**Keep it safe:**

- Use keys dedicated to CI, each with a spend cap, so even a worst case is bounded.
- Keep the workflow trigger as `workflow_dispatch` (or pushes to your own
  branches). Never `pull_request_target`, which would run fork code with secrets.
- Pin third-party actions to a commit SHA, and rotate the keys after a public demo.

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

Each run is a loop of a Tavily search and a Nemotron completion, plus the version
resolve, so when a remediation goes wrong you want to see those steps. Set
`LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY=...` and every run, model call,
search, and resolve is traced to LangSmith under the `LANGSMITH_PROJECT` project.
With the flag or key unset, tracing is a transparent no-op and LangSmith is not
even imported, so LiveFix has no hard dependency on it.

## Tests

```bash
python -m pytest tests/ -q
```

The tests stub the Nebius and Tavily SDKs, so they run with no keys and no
network.

## License

MIT. See [LICENSE](LICENSE).
