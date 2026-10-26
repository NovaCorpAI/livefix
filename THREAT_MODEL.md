# Threat model

LiveFix is an agent that edits code and dependency manifests and can open pull
requests, so it is worth being precise about what it is allowed to do, what it is
not, and why it is safe to run in CI. This is the short, honest version.

## What the agent can do

- Read files inside the target project directory.
- Edit the dependency manifest (pin bump) and the source files named in a failing
  test's traceback.
- Run the project's own test command.
- Call two external services: Nebius Token Factory (the model) and Tavily (web
  search). Optionally emit a LangSmith trace.
- In the GitHub Action, open a pull request and set a commit status on it.

## What the agent cannot do

- **Write outside the project.** Every file it is about to write is resolved to an
  absolute path and checked to be inside the project directory; a path that
  escapes is skipped, not written (`LiveFixAgent._apply`, `Remediator.remediate`).
- **Ship an unverified change.** Nothing is reported as remediated unless the
  project's own tests pass afterward. The `LiveFix / remediation-verified` check is
  green only on a real test pass; the step exits non-zero otherwise.
- **Apply a syntactically broken fix.** A proposed file that does not parse is
  rejected and the loop retries instead of writing it: Python via `ast.parse`,
  JavaScript via `node --check`.
- **Pass a test by rewriting the test.** The test is the spec the fix is verified
  against, so the agent never writes to a test file (`test_*.py`, `*.test.js`,
  anything under a `test/`, `tests/` or `__tests__/` directory, etc.). Test files
  are shown to the model as read-only context; only non-test source is edited
  (`_is_test_file`, used by `_apply` and `_changes_something`).
- **Loop forever.** The repair loop is bounded (default five iterations) and stops
  early when an iteration changes nothing.
- **Merge anything.** It opens a PR; a human still reviews and merges.

## Secrets

- API keys live in the environment, never in the code or the repository. For the
  CLI they sit in a git-ignored `.env`; for the Action they are encrypted
  repository secrets, masked in logs, and never exposed to pull requests from
  forks.
- Recommended: dedicated CI keys with a spend cap, the workflow kept on
  `workflow_dispatch` (never `pull_request_target`, which would run fork code with
  your secrets), third-party actions pinned to a commit SHA, and keys rotated
  after a public demo. See the README's "Connect your credentials" section.

## Untrusted input

The model reads live web search results (Tavily) and a failing test's output.
These are treated as data for one narrow decision each: the minimal safe version,
and which files to repair. The model never executes fetched content; the only code
that runs is the project's own test command, which the project owner chose.

## Residual risk, stated plainly

- The model can still propose a wrong-but-valid fix. The test gate is the backstop:
  a wrong fix that fails the tests never ships, and a wrong fix that passes the
  tests is, by definition, as good as the tests are. LiveFix is a force multiplier
  on your test suite, not a replacement for it.
- Web search can be wrong or stale. When it cannot ground a safe version, the model
  abstains rather than guessing, and LiveFix reports that it could not remediate.
