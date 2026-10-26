# LiveFix (Devpost submission copy)

> An autonomous agent that remediates a vulnerable dependency end to end: it
> resolves the safe version from the live web, bumps the pin, and repairs the
> code the upgrade breaks, verified by your tests. Runs on Nebius Token Factory
> with an NVIDIA Nemotron open model, grounded by Tavily live web search.

Live demo: https://livefix.novacorplabs.com

## Inspiration

Exploitation of vulnerabilities just became the single most common way breaches
start, ahead of stolen credentials, and the median time to actually patch a known
flaw climbed to 43 days and is still rising (Verizon 2026 Data Breach
Investigations Report). The tools that *find* vulnerable dependencies are
excellent and everywhere: Dependabot, Snyk, Renovate, Mend. But every one of them
stops at the same wall. They open a version-bump PR and walk away, and the PR sits
there red because the upgrade broke the build.

That last mile is exactly what an agent should own, and it is two walls, not one.
First, *which version is even safe?* A CVE disclosed this month post-dates every
model's training cutoff, so a plain model cannot know the fixed version. Second,
the safe version is often a major release that removed an API you used, so the
patch that closes the CVE turns your tests red. We wanted an agent that closes
both: resolves the real safe version from the live web, and lands the upgrade
green.

## What it does

LiveFix takes a project, a vulnerable package, and an advisory id, and remediates
it in one pass:

1. **Resolve** the minimal safe version by searching the live web with Tavily.
   This is the fact a plain model cannot supply for a fresh CVE.
2. **Bump** the dependency pin in the manifest to that version.
3. **Repair** whatever the upgrade broke: it runs the failing test, locates the
   file in the traceback (with a path-escape guard), and has NVIDIA Nemotron
   rewrite it, grounded in the current docs.
4. **Verify** by re-running the project's tests, looping until green.

The output is a merge-ready change instead of a rotting bump PR.

## How we built it

- **Model:** `nvidia/nemotron-3-super-120b-a12b` on **Nebius Token Factory**,
  through the OpenAI-compatible endpoint, so the official `openai` SDK worked
  unchanged against Nebius with just a base URL and key.
- **Grounding:** **Tavily** `search_depth="advanced"` for the live advisory and
  the current migration docs.
- **Agent:** a small, dependency-light Python package (`livefix/`): a version
  resolver, a manifest pin editor, a test runner, a traceback-to-file resolver,
  a brace-scanning JSON parser with a temperature-escalating retry, and the
  repair loop. The repair loop rejects a model reply that parses but changes
  nothing, so it keeps trying instead of giving up.
- **Observability:** optional **LangSmith** tracing on the resolve, the loop, the
  model call, and the search, as a transparent no-op when unconfigured.
- **Demo surface:** a hosted page on **Vercel** that replays a real recorded
  remediation.
- **Trust layer:** every remediation PR carries an honest signature (a one-line
  summary, a collapsed detail block, and a machine-readable commit trailer) plus a
  `LiveFix / remediation-verified` check that goes green only when tests pass. It
  says *remediated and verified by tests*, never that a human reviewed it.
  `action.yml` packages the whole flow as a reusable GitHub Action.

## How we proved it works

We did not want to assert that web search helps, so we measured it, and we were
honest about what we found.

The load-bearing claim is that a plain model cannot name the safe version for a
fresh CVE. `benchmark/security/` gives the same Nemotron model five real,
2026-disclosed CVEs across two ecosystems (Pillow, Brotli and urllib3 on PyPI,
node-tar on npm) and asks for the minimal safe version, with the live web on and
off. The result: **15/15 correct with Tavily, 0/15 without.** And without the web
the model does not hallucinate, it **abstains**: it knows it cannot know. That is
the gap Tavily fills, and it is impossible to fake.

We also measured the code-repair step on its own (`benchmark/`, five pre-cutoff
breakages). There a strong model repairs with or without search, because it
already knows those APIs. So we do not overclaim: the web's decisive contribution
is the post-cutoff **fact**, not out-reasoning the model on code it understands.
Being precise about that is, we think, a feature of the submission, not a
weakness.

The end-to-end example (`examples/vulnerable_project/`) fuses both: Pillow 12.3.0
is vulnerable to CVE-2026-112398, the fix only ships in Pillow 13.0.0, and that
release removed `ImageCmsProfile.product_name`. LiveFix resolves 13.0.0 from the
web, bumps the pin, rewrites the code to `ImageCms.getProfileName`, and the test
passes.

And it generalizes beyond a one-line swap. A second example
(`examples/profile_service/`) breaks in three modules at once, because Pillow 13
removed three attributes it reads (`product_name`, `product_desc`,
`product_copyright`), and LiveFix repairs each in turn until the whole build is
green. Both examples run as the real GitHub Action, which opened two signed,
verified pull requests on the repo (PR #1, one file; PR #2, three files).

None of the benchmark is invented: every CVE is real and checkable. We cross
checked each one against NVD and OSV, and every safe version we grade against
matches the authoritative GitHub Advisory Database fixed version;
`benchmark/security/GROUND_TRUTH.md` has one-click links so a judge can verify any
row in seconds.

## Where LiveFix fits, and the business behind it

LiveFix is not another scanner. It is the missing last mile of the pipeline every
scanner already feeds: scan, alert, bump PR, and then today either a human or a PR
that rots. We sit on top of the scanner you already run and close the loop it
opens, turning a red bump PR into a green, merge-ready change. So the wedge is a
partnership, not a fight: Dependabot, Snyk and Renovate tell you what is broken;
LiveFix lands the fix. The category (software composition analysis and
vulnerability management) is large and well funded, and the one step everyone has
left to the developer, actually remediating the break, is exactly the step a live-
grounded agent can now take.

The business follows directly: a GitHub App billed per repository, or per
remediated advisory for high-volume orgs, triggered by the scanner alert teams
already receive. The value lands in the metric security leaders now report to
their board, mean time to remediate: every advisory LiveFix turns green is
engineer-hours saved and days shaved off an MTTR that regulation (the EU Cyber
Resilience Act, the SEC disclosure rules) is turning into a hard obligation.

The unit economics are stark, and we measured them on real runs: a one-file
remediation costs about half a cent or less in model compute (roughly 6,000 to
9,000 tokens) in about fifteen seconds; a three-file remediation about one cent
(roughly 22,000 tokens) in about a minute. That is against the one to three
engineer-hours a breaking security upgrade takes a senior to resolve by hand.
LiveFix reports the exact tokens and estimated cost on every run.

## Challenges we ran into

- **Measuring the right thing.** Our first benchmark used well-known API changes
  and showed no gap: the model already knew them. That sent us to the one place
  live search is undeniably load-bearing, freshly disclosed CVEs, and the gap
  appeared, clean.
- **Guaranteed JSON, and no-op replies.** The model sometimes wrapped its JSON in
  prose, or returned the file unchanged. We added a parser that scans for the
  first object with a `files` key, a temperature-escalating retry, and a check
  that rejects a reply that changes nothing. (Written up in `FEEDBACK.md` as our
  top platform ask: a native JSON-output mode.)
- **Safety of file writes.** An agent that rewrites files and manifests must never
  escape the project; every target path is resolved and checked before a write.

## Accomplishments we are proud of

- A working, safe, end-to-end remediation in a small, readable codebase, proven
  live: the GitHub Action opened two signed, verified PRs, one of them repairing a
  break that spanned three files.
- A benchmark that turns the core claim into a clean number (15/15 vs 0/15) on
  five real, independently verifiable 2026 CVEs across two ecosystems, plus the
  intellectual honesty to show where the web does *not* help.
- Concrete, actionable platform feedback from genuinely building on the stack.

## What we learned

The OpenAI-compatible endpoint makes Nebius trivial to adopt from existing code,
and Nemotron produces correct, minimal patches. The sharpest lesson: a strong
model already knows the public API ecosystem deeply, so live search earns its
place not by writing code the model can't, but by supplying facts the model
cannot have, like a vulnerability disclosed days ago.

## What's next

- **Shipped:** a reusable GitHub Action (`action.yml`) that remediates and opens a
  signed, verified PR. Next is wiring it to a scanner alert (a Dependabot webhook
  or a scheduled `pip-audit`) so it fires on its own.
- Tamper-evident attestation (Sigstore / SLSA provenance) on every remediation,
  signed by NovaCorp Labs, as the paid trust layer for compliance (EU CRA, SEC).
- More manifests (pyproject/poetry/lock files) and ecosystems (npm, cargo).
- A LangSmith evaluation that scores remediations across a growing CVE set.
- A human escalation path when the loop exhausts its budget, so the agent knows
  when to ask for help instead of failing silently.

## Built with

Python, Nebius Token Factory, NVIDIA Nemotron, Tavily, LangSmith, OpenAI SDK,
pytest, Pillow, Vercel.
