# Builder feedback: Nebius Token Factory + Tavily

Honest friction we hit building LiveFix (a self-healing-test agent) end to end on
the Nebius x NVIDIA stack, with the fix we would suggest for each. Ordered by how
much it slowed us down. Everything here is something we actually ran into, not a
wishlist.

## 1. Strict JSON output needs a native mode (Nebius Token Factory)

LiveFix asks the model for one JSON object: `{"explanation": ..., "files":
{path: content}}`. Nemotron (`nvidia/nemotron-3-super-120b-a12b`) is good at this
but not reliable at it: it sometimes wraps the JSON in prose or a markdown fence,
or emits reasoning before the object. We had to defend against that with a
brace-scanning parser and a retry loop that escalates temperature (0.0, then 0.3,
then 0.6) until an object parses.

- **Impact:** real added code and latency, and an occasional iteration lost to an
  unparseable reply.
- **Suggestion:** support OpenAI-style `response_format={"type": "json_object"}`
  (and ideally a JSON schema / tool-calling path) on the Token Factory endpoint,
  documented per model. For an agent that parses every reply, guaranteed JSON is
  the single highest-value feature.

## 2. The exact base URL was easy to get wrong (Nebius Token Factory)

The OpenAI-compatible base URL is `https://api.tokenfactory.nebius.com/v1/`, but
confirming that (vs a region-suffixed host) took a dashboard dig. A wrong base URL
fails as a generic connection or auth error, which is slow to diagnose.

- **Suggestion:** show the full, copy-pasteable base URL next to the API key on
  the key-creation screen, and name clearly when a region-suffixed host is
  required. The "Start building" snippet already hardcodes it, which is great;
  surfacing it on the key screen too would close the gap.

## 3. Credits are hard to see and reconcile (Nebius Token Factory)

As a new AI Builder Program member:

- `.../settings/billing` returned a Not found page; the live billing lives under a
  different path, and the product domain (studio vs tokenfactory) added confusion.
- The dashboard showed a small trial balance, while the $25 program credit arrives
  in a **separate email** and was not visible in-app at the same time, so it was
  not obvious whether it had been granted.
- Transactions showed trial grant and consumption but no clear "program credit:
  pending/applied" line.

- **Suggestion:** one Credits page that lists every grant (trial, program,
  partner) with status (pending, active, expired) and amount, reachable from the
  top-bar balance. It would remove all doubt about whether a credit landed.

## 4. OpenAI-compat parity for reproducibility is undocumented (Nebius Token Factory)

Building a benchmark, we wanted reproducible runs, which means knowing whether the
endpoint honors `seed` (and `response_format`, see #1). We could not find this
stated per model.

- **Suggestion:** a short "OpenAI compatibility" matrix per model: which request
  fields are honored (`seed`, `response_format`, `tools`, `logprobs`,
  `max_tokens` semantics), and the context window. It directly enables honest
  eval and benchmarking on the platform.

## 5. Credit-to-dollar mapping is implicit (Tavily)

Tavily bills in credits; the $25 program credit showed up as "+3,125 add-on
credits". The 0.008 USD/credit rate is on the pricing page, so the math checks
out, but surfacing the dollar value of a granted credit next to the credit count
would make it instantly legible.

- **Suggestion:** on the Billing overview, show granted add-on credits with their
  dollar equivalent and source (for example "AI Builder Program, $25").

## What worked well (so the signal is balanced)

- The OpenAI-compatible endpoint meant the official `openai` Python SDK worked
  unchanged against Nebius: just a base URL and key. That is the reason the agent
  was small.
- Tavily `search_depth="advanced"` returned genuinely useful, current
  documentation snippets for post-cutoff API changes, which is the whole premise
  of LiveFix and it held up.
- Nemotron produced correct minimal patches when grounded with those snippets.

If any of the above is already solved and we missed it, point us at the doc and we
will update this file; the aim is useful signal, not a complaint list.
