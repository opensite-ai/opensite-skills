---
name: deep-research-agent-architecture
description: "Design Forge's Phase 4B deep-research subsystem so every claim in a generated report traces to a fetched source. Load when building or reviewing a multi-source research agent, planner/executor separation, parallel subagent fan-out, source adapters over src/scraping/ tiers, citation verification, claim-level entailment or faithfulness checks, hard-fail on unverifiable citations, report artifacts in Tigris, context-budget management for long syntheses, per-request cost caps for research aliases, or any request shaped as 'add deep research' / 'generate a cited report' / 'why are the citations wrong'."
license: Apache-2.0
metadata:
  version: '1.0'
  author: encapsa-forge
---

# Deep Research Agent Architecture

Phase 4B (deep research) is **not yet built** in Forge. This skill is the design contract for
building it as a first-class backend subsystem rather than a prompt. Forge is live in production;
anything added rides existing controls or it does not ship.

## Start here: the citation problem

A human audit of four commercial generative search systems (Bing Chat, NeevaAI, perplexity.ai,
YouChat) found that on average only **51.5% of generated sentences are fully supported by their
citations**, and only **74.5% of citations support their associated sentence** — the authors
describe these systems as carrying a "facade of trustworthiness"
([Liu, Zhang & Liang, arXiv 2304.09848](https://arxiv.org/abs/2304.09848)). ALCE, the reference
benchmark for automatic citation evaluation, finds that on ELI5 **even the best models lack
complete citation support 50% of the time** ([Gao et al., arXiv 2305.14627](https://arxiv.org/abs/2305.14627)).
OpenAI's own Deep Research page states that the system **can hallucinate facts and make incorrect
inferences**, may fail to distinguish authoritative information from rumor, shows **weak
confidence calibration**, and often fails to convey uncertainty
([OpenAI: Introducing deep research](https://openai.com/index/introducing-deep-research/)).

Read those numbers as a specification, not a caveat. Roughly half of the sentences a
state-of-the-art system emits are not fully supported by what they cite. So:

**Citation validation cannot be advisory.** It is not a quality score attached to a finished
report; it is a gate the report must pass to exist. Forge's Phase 4B exit criterion is that
**every cited fact traces to a fetched source**, and the design rule is **hard-fail on
unverifiable citations** — the claim is dropped or the request errors, never emitted with a
warning. A warning attached to a plausible-looking citation list is worse than no citation at
all, because it transfers verification cost to the reader while presenting the artifact of a
verified system.

## When to Use This Skill

- Building or reviewing Phase 4B: planner, executors, source adapters, synthesis, verification.
- Adding a research alias to `FORGE_LLM_MODELS`, or arguing about which model the report generator
  and the verifier should be.
- Any change to how citations are emitted, stored, or checked.
- Reviewing a research report artifact for defensibility, or diagnosing a fabricated citation.
- Sizing cost caps, iteration caps, or fan-out width for a research request.
- Deciding whether a request needs multi-agent research at all — most do not.

Read `references/citation-verification-protocol.md` before implementing or reviewing the
verification pass; it holds the two-stage procedure, the hard-fail matrix, and the test shapes.

## Non-negotiables

1. **No URL enters a report unless it is in the session's fetch log.** Reachability is checked
   against what this request actually fetched, not against the open internet. This mechanically
   eliminates fabricated links.
2. **Every emitted claim carries a verdict from the claim-support check.** Unsupported claims are
   dropped, not softened. An explicit `n.a.` beats an unsupported value.
3. **Every research request carries a hard token and cost cap**, enforced in the request path, not
   in the prompt.
4. **Iteration is capped.** Forge's Document AI loop caps at 5; the research refinement loop gets
   the same treatment.
5. **The research path rides `LlmRouter`.** No direct provider calls. That is what keeps PHI
   gating, provenance filtering, guardrails, and audit on the research model. Filter order stays
   HIPAA -> Provenance -> Capability.
6. **Source adapters go through `src/scraping/`** and inherit `ssrf.rs` and `robots.rs`. A research
   agent that fetches arbitrary model-chosen URLs without SSRF controls is a server-side request
   forgery primitive with a friendly name.
7. **The audit record names the sources fetched.** Metadata only — URL, status, content hash,
   timestamp, tier — never body content.

## Architecture

```
request -> planner -> [executor fan-out] -> dedup/recency -> synthesis -> verification -> artifact
             |             |                                    |             |
             |         source adapters                     long-context   cheaper model
             |         (src/scraping tiers)                  model         + entailment
             |                                                                 |
             +-- cost/iteration governor <-------- fetch log (append-only) ----+
```

### Planner / executor separation

Anthropic's published design is orchestrator-worker: a **lead agent** analyzes the query, develops
strategy, decomposes into subtasks, spawns subagents, and compiles the final answer; **subagents**
run in parallel as intelligent filters, iteratively searching and condensing. This is explicitly
contrasted with static RAG, which retrieves the chunks most similar to the query once
([Anthropic: How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)).

Their effort-scaling heuristics, encoded in the prompt, are the most useful published sizing
numbers ([same post](https://www.anthropic.com/engineering/multi-agent-research-system)):

| Query class | Agents | Tool calls |
|---|---|---|
| Simple fact-finding | 1 | 3–10 |
| Direct comparison | 2–4 subagents | 10–15 each |
| Complex research | >10 subagents, clearly divided responsibilities | — |

The lead spawns **3–5 subagents in parallel**, and each subagent uses **3+ tools in parallel**.
Every subagent task must specify **objective, output format, tool/source guidance, and
boundaries**. Their failure example is the one to internalize: on "research the semiconductor
shortage," one subagent researched the 2021 automotive chip crisis while two duplicated 2025
supply-chain work ([same post](https://www.anthropic.com/engineering/multi-agent-research-system)).
Task boundaries are the deduplication mechanism at the planning layer.

Documented failure modes from the same post: spawning **50 subagents** for simple queries, endless
searching for nonexistent sources, and synchronous execution blocking on a single slow subagent —
the lead cannot steer running subagents, and subagents cannot coordinate with each other. And when
multi-agent is *not* worth it: domains where all agents need the same context, tasks with many
inter-agent dependencies, and **most coding tasks**.

Forge implication (not from a doc): make the planner's effort tier an **explicit, logged, capped
field** on the request rather than a model decision. The planner proposes a tier; the governor
clamps it against the caller's cost cap. A model that can spawn 50 subagents will.

### Source adapters

Adapter contract (not from a doc): `search(query) -> Vec<Candidate>` and
`fetch(url) -> FetchedDoc`, where every `fetch` appends to the append-only session fetch log with
URL, final URL after redirects, HTTP status, content hash, tier used, and timestamp. The fetch log
is the ground truth for verification. If a document is not in the log, it does not exist.

- **Web** rides the existing Forge scrape tiers: `src/scraping/tier1.rs` (static),
  `tier2.rs` (browser), `tier3.rs`, with `escalator.rs` deciding escalation and `extractor.rs` /
  `dom_smoothie` producing readable text. Budget hierarchy is already set in `fly.toml` and must
  stay nested innermost-smallest: `SCRAPE_TIER1_TIMEOUT_MS=8000`,
  `SCRAPE_TIER2_SETTLE_CAP_MS=35000` < `SCRAPE_TIER2_TIMEOUT_MS=55000`,
  `SCRAPE_TIER3_TIMEOUT_MS=45000`, with `SCRAPE_BROWSER_POOL_SIZE=3` and
  `SCRAPE_TIER2_MAX_CONCURRENCY=2`. Those last two are the real ceiling on research fan-out
  width on a `performance-4x` machine — a planner that wants 10 parallel browser fetches will
  serialize behind a pool of 3.
- **Per-vertical adapters** (academic, code/repo, internal document stores) are separate
  implementations of the same trait, not special cases inside the web adapter. Anthropic's rule:
  agents should search **the source that actually holds the context** — web search is the wrong
  tool when the content lives only in Slack ([same post](https://www.anthropic.com/engineering/multi-agent-research-system)).
- **Query strategy**, from the same post: prefer primary sources over SEO-optimized content farms,
  and **start wide, then narrow** rather than opening with long specific queries. Their human
  testers caught a systematic model preference for SEO content farms over authoritative sources —
  so source-quality scoring belongs in the adapter, not in the prompt.

### Dedup and recency

No published deduplication or recency-scoring algorithm for research agents was found in the
compiled research (`n.a.`). The following is design guidance, **not from a doc**:

- Dedup at three levels: exact URL (after redirect normalization and tracking-param stripping),
  content hash (`blake3`, already a Forge dependency), and near-duplicate text via embedding
  similarity using the existing embeddings surface. Syndicated news is the case that defeats
  URL-only dedup, and it inflates apparent corroboration — three copies of one wire story read as
  three sources.
- Never let dedup silently drop a source that a claim already cites. Merge into a canonical
  document with an alias list, so the citation still resolves.
- Recency: require the adapter to return an explicit `published_at` when available and `None`
  otherwise. Never infer a date from page text. Make staleness a **planner input** (the planner
  decides whether the question is time-sensitive) and a **report field**, not a silent ranking
  weight — a hidden recency boost is unauditable.

### Context-budget management for long syntheses

From Anthropic's post: summarize completed phases, store essentials in external memory, retrieve
artifacts such as the research plan on demand, and **spawn fresh subagents with clean contexts**
when limits approach, with careful handoffs. For large artifacts, have subagents write to
**external storage and pass lightweight references** back to the coordinator — this avoids
information loss through multi-stage summarization and the token cost of copying outputs into
conversation history, and works best for code, reports, and visualizations
([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).

Forge mapping (not from a doc): subagent outputs go to Tigris; the coordinator holds keys and
digests. This matters more here than in a generic agent because **the verifier must read the
fetched span, not a summary of it** — a summarize-then-verify pipeline verifies the summary and
proves nothing. Retain the raw fetched text, addressed by content hash, for the life of the
request.

Also from the same post, production engineering rules worth copying directly: durable execution
with **regular checkpoints** so a failure resumes instead of restarting; tell the model when a
tool is failing and let it adapt; full production tracing that monitors decision patterns at a
high level **without reading conversation contents** (which is also what Forge's audit invariants
require); and **rainbow deployments** — run old and new versions simultaneously and shift traffic
gradually, because agents may be mid-run during a deploy.

## Cost honesty

Anthropic's published numbers, from their internal research eval and BrowseComp
([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)):

| Finding | Value |
|---|---|
| Multi-agent (Opus 4 lead + Sonnet 4 subagents) vs. single-agent Opus 4, internal research eval | **+90.2%** |
| Variance explained on BrowseComp by token usage + tool calls + model choice | **95%** |
| Variance explained by **token usage alone** | **80%** |
| Agent vs. chat token usage | **~4x** |
| **Multi-agent vs. chat token usage** | **~15x** |
| Parallel tool calling effect on research time for complex queries | up to **-90%** |
| Rewritten tool description (by a tool-testing agent) effect on task completion time | **-40%** |
| Early prompt tweak effect on success rate | **30% -> 80%** |
| Initial eval set size that was already informative | **~20 queries** |

State it plainly: **a research agent is a token-cost multiplier.** Roughly 15x chat tokens buys
+90.2% on their eval, and since token usage alone explains 80% of BrowseComp variance, the
quality is substantially *bought* rather than engineered. Two consequences:

1. **Every research request must carry a per-request cost cap**, enforced by a governor in the
   request path that counts tokens across all subagents and the verifier, and terminates with a
   partial-but-verified report when the cap is hit. Not a prompt instruction. Not a post-hoc
   dashboard.
2. **Only justify multi-agent where the answer is worth the tokens.** The default for a
   single-fact question is one agent and 3–10 tool calls. Route by effort tier and log the tier.

Reference points on Forge's own cost surface: the primary inference endpoint is 4xH200 at
approximately **$23.72/hr while running**, and an always-on worker is roughly **$570/day** (D-20).
Cold starts are accepted with Active workers 0 and FlashBoot on. A research request that fans out
to 10 subagents against a long-context alias on that hardware is a materially different cost
event from a `/v1/generate` call, and the caller must be told the tier before it runs.

OpenAI's Deep Research reports task durations of **5–30 minutes**
([OpenAI](https://openai.com/index/introducing-deep-research/)) — this is not a request/response
shape. Design it as an async job with checkpoints from the start, not as a long HTTP handler that
will collide with Fly's `kill_timeout = '300s'`.

## Retrieval quality over model size

The BrowseComp variance decomposition is the argument: token usage plus tool calls plus model
choice explain 95% of variance, and **token usage alone explains 80%**
([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)) — so what the
agent read dominates which model read it. Anthropic's own tooling result points the same way: a
rewritten tool description cut task completion time **40%**, and an early prompt tweak moved
success from **30% to 80%** ([same post](https://www.anthropic.com/engineering/multi-agent-research-system)).
Both are retrieval-side, not model-side. STORM's contribution is also pre-writing: discovering
diverse perspectives and simulating perspective-carrying question-asking before any prose is
generated, which produced articles judged **organized (+25% absolute)** and **broad in coverage
(+10%)** versus an outline-driven RAG baseline on FreshWiki
([Shao et al., arXiv 2402.14207](https://arxiv.org/abs/2402.14207)).

Model assignment (not from a doc, but follows directly):

| Stage | Model class | Why |
|---|---|---|
| Planner | mid-tier, cheap | decomposition is a short structured task; cap its output shape with `/v1/generate/structured` |
| Executors / subagents | mid-tier | they are filters; Anthropic used Sonnet subagents under an Opus lead |
| Synthesis / report generator | **long-context** | must hold many fetched spans plus the outline without multi-stage summarization, which is where information loss and unsupported claims enter |
| Verification | **cheaper, smaller** | per-claim entailment over one span is a short, narrow, high-volume task; running it on the expensive alias multiplies the 15x again for no accuracy gain |

Anthropic's production judge finding supports the cheap-verifier choice: after testing multiple
judges per component, **a single LLM call with a single prompt** was the most consistent and best
aligned with human judgment, emitting a 0.0–1.0 score plus pass/fail
([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Their rubric also
separates **factual accuracy** ("do the claims match the sources?") from **citation accuracy**
("do the cited sources match the claims?"), plus completeness, source quality (primary over
secondary), and tool efficiency — that separation is the shape of the two-stage gate below.

## The distinction most implementations collapse

Two different properties get called "citation validation":

| Check | Question | Method | Is it the gate? |
|---|---|---|---|
| **Stage 1 — existence/reachability** | Is this URL real, and did *this request* fetch it? | membership test against the session fetch log; status and content hash present | No. Necessary, cheap, and insufficient. |
| **Stage 2 — claim support** | Does the fetched content actually support this specific sentence? | entailment / faithfulness check of the claim against the **fetched span** | **Yes. This is the only real gate.** |

Systems that ship Stage 1 alone report a healthy citation rate and still fail at the documented
51.5% sentence-support level, because a reachable, correctly-formatted, topically-related citation
that does not entail the sentence passes Stage 1 perfectly
([arXiv 2304.09848](https://arxiv.org/abs/2304.09848)).

Claim-level verification pass — the required shape:

1. **Decompose** the draft into atomic claims. Sentence granularity at minimum; sentence-level is
   where the 51.5% failure is measured, so document-level verification cannot see it.
2. **Resolve** each claim's citation to a `(document_hash, char_start, char_end)` span in the
   retained fetched text.
3. **Check entailment over the fetched span, never over a summary.** Verifying against a summary
   verifies the summarizer. If the span is too large for the verifier's context, split the span
   and require at least one sub-span to entail; do not compress it.
4. **Verdicts:** `supported` / `partially_supported` / `unsupported` / `unresolvable`. Only
   `supported` may be emitted as a cited assertion. `partially_supported` must be rewritten to the
   supported subset or dropped. `unsupported` and `unresolvable` hard-fail the claim.
5. **Numbers are checked as numbers.** Every figure, date, percentage, and proper name in the
   claim must appear in or be arithmetically derivable from the span; label derived arithmetic as
   derived and show its inputs. Entailment scoring alone is too tolerant of a transposed digit.
6. **Prefer explicit `n.a.` to an unsupported value.** That is the discipline OpenAI identifies as
   missing when it flags weak confidence calibration
   ([OpenAI](https://openai.com/index/introducing-deep-research/)).

No fetched source documents a production hard-fail gate — the two-stage design and the verdict
taxonomy are **not from a doc**; they follow from the measured failure rates above. Full
procedure, hard-fail matrix, and test shapes: `references/citation-verification-protocol.md`.

STORM's expert reviewers surfaced two failure modes that Stage 2 does **not** catch, and they need
naming in any design review: **source bias transfer** and **over-association of unrelated facts**
([arXiv 2402.14207](https://arxiv.org/abs/2402.14207)). Both produce claims that are individually
entailed by their sources and collectively misleading. Entailment is a floor, not a ceiling.

## Report artifact design

- **Structured output with inline citations.** Emit the report through
  `/v1/generate/structured` (xgrammar) against a schema where every claim node carries a citation
  reference. Note the tradeoff and design around it: format restriction causes a significant
  decline in LLM reasoning ability, and stricter constraints degrade more
  ([Tam et al., arXiv 2408.02442](https://arxiv.org/abs/2408.02442)); magnitudes were not stated on
  the abstract page. Mitigation (not from a doc): reason and draft in free text, then emit a
  constrained second pass that carries the citations. Also note structured generation has **no
  fallback** in Forge — `AnthropicProvider` returns terminal `capability_not_supported` for
  `generate_structured` (D-9, D-26) — so the constrained emit step is a single-provider dependency
  and needs an explicit degraded path (emit unconstrained plus a validator) rather than a hard
  failure.
- **Artifact storage in Tigris**, content-addressed by `blake3`, alongside the fetched-document
  corpus for the request. Forge has **no direct database dependency** — Cargo.toml states
  verbatim: "Forge is a stateless inference service — no direct DB dependency. DB writes … are
  the caller's responsibility." Persisting research state in Postgres from Forge is out of
  contract; Octane owns any DB rows.
- **Re-renderability.** Store the structured intermediate, not just rendered markdown, so the same
  report can be re-emitted in another format and, more importantly, **re-verified later** against
  the retained fetched corpus. A report you cannot re-verify is not auditable.
- **Audit record: which sources were fetched.** Per source: URL, final URL, status, tier, content
  hash, timestamp, and the verdict counts it supported. Metadata only, never body content — this
  matches Forge's existing audit invariants (metadata only, caller identities as unsalted BLAKE3
  digests per D-7, tenant IDs raw per R-2C-H). Note that scraping telemetry already logs raw
  target hostnames deliberately (D-8), so hostname logging here is consistent with an existing
  ruling rather than a new one.

## Forge-specific mapping

Marked **not from a doc** — Phase 4B is unbuilt and this is design guidance, not repo content.
Read the actual files before implementing; do not assert Forge internals from this section.

| Concern | Mapping |
|---|---|
| Model access | Rides the existing `LlmRouter` so PHI gating and provenance filtering apply to the research model. `LlmRouter` is a coordinator and deliberately does **not** implement `LlmProvider` (src/llm/mod.rs:3-5, router.rs:41-43) — do not wrap it to make research calls convenient; that is exactly the filter-semantics loss the design prevents. |
| PHI | A research request whose prompt carries PHI must fail closed with `PhiPolicy` like any other. Every roster entry is `hipaa_eligible: false` until the RunPod BAA is signed (D-5). Research over PHI is not available until that changes. |
| Provenance | A tenant policy must include `"Us"` in `allowed_provenances` or the Anthropic fallback is dead for that tenant (D-4). If the research alias's only long-context option is Anthropic, tenants without `"Us"` have **no research path** — surface that at config-validation time, not at request time. |
| Source adapters | Reuse `src/scraping/` tiers and **must** respect the existing `ssrf.rs` and `robots.rs` controls. Model-chosen URLs are untrusted input. |
| Fan-out ceiling | `SCRAPE_BROWSER_POOL_SIZE=3` and `SCRAPE_TIER2_MAX_CONCURRENCY=2` bound real parallel browser fetches; the planner's requested width must be clamped to them, not queued behind them invisibly. |
| Artifacts | Tigris (`object_store` 0.14.1, aws). Note **no conditional delete** upstream in `object_store` 0.14.1 — do not design an artifact lifecycle that depends on compare-and-delete. |
| Deadlines | The known sharp edge applies: the effective overall request deadline behaves as `max(timeout_secs)` across the chain (config.rs:85-93, router.rs:678-686), so a slow first provider consumes the whole budget and the fallback never runs — root cause of a real `DeadlineExceeded` storm on 2026-08-23. A long-context research alias with a large `timeout_secs` will extend the overall budget for the whole chain. Give research its own alias and its own budget; do not raise timeouts on a shared chain. |
| Cost caps | Per-request cost caps matter specifically because the research alias is intended to be a long-context model on expensive hardware. Enforce in the governor. |
| Async shape | `kill_timeout = '300s'` on `opensite-forge`, and research tasks run 5–30 minutes in comparable systems ([OpenAI](https://openai.com/index/introducing-deep-research/)). Job + checkpoints + resumable state, not a long-lived HTTP handler. |
| Metrics | The metric label taxonomy is a **bounded namespace by contract** — every label value must be code-defined-static, registry-bounded, or provenance-gated (D-23a). Do not add per-source-host or per-query metric labels; a new label value class needs a ruling, not a PR. |
| Rate limiting | `governor` per-model rate limiting already exists per provider entry. Subagent fan-out will hit it. Clamp fan-out to the alias's `rps`, or the fan-out becomes a self-inflicted 429 storm. |

## Verification

How to prove the subsystem is correct. These are the checks, not sentiment.

1. **Fabricated-URL test.** Feed a synthesis step a citation to a URL that was never fetched.
   Expected: the claim is hard-failed at Stage 1, the request records a `citation_unresolvable`
   event, and the URL never appears in the artifact. Assert on the artifact, not the log.
2. **Unsupported-claim test.** Construct a claim that is topically related to a real fetched
   document but not entailed by it (the documented 51.5% failure shape). Expected: Stage 1 passes,
   Stage 2 returns `unsupported`, and the claim is dropped. A pipeline that emits it has no gate.
3. **Summary-substitution test.** Run the verifier against a summary of the fetched document
   instead of the span. Expected: the harness refuses, because verification must read the fetched
   span. This test exists to keep the shortcut from being reintroduced.
4. **Number-fidelity test.** Perturb a single digit in a cited figure. Expected: `unsupported`.
   If entailment scoring alone passes it, the numeric check is missing.
5. **Cost-cap test.** Set a cap below the cost of the planned fan-out. Expected: the governor
   terminates, returns a partial report whose every remaining claim is `supported`, and marks it
   partial. Never an over-cap completion, never an unverified partial.
6. **Iteration-cap test.** Give the agent a question with no answerable source (the documented
   "endless searching for nonexistent sources" failure). Expected: termination at the cap with an
   explicit "not found" report, not an invented answer.
7. **SSRF and robots test.** Have the planner emit `http://169.254.169.254/`, a `.internal`
   Fly 6PN host, and a `robots.txt`-disallowed path. Expected: all rejected by
   `src/scraping/ssrf.rs` and `robots.rs` before any fetch, and each rejection recorded.
8. **Re-verification test.** Re-run verification over a stored artifact plus its retained corpus
   with no network access. Expected: identical verdicts. If it cannot run offline, the corpus was
   not retained and the artifact is not auditable.
9. **Audit-completeness test.** Every URL in the artifact appears in the audit record's fetched-
   source list, and the audit record contains **zero** body content. Assert both directions.
10. **Eval set.** Build the citation eval before the agent, starting at roughly **20 queries** —
    Anthropic found that size already informative ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).
    Report **sentence-level support rate** and **citation-support rate** as the two headline
    metrics, because those are the two numbers the literature measures
    ([arXiv 2304.09848](https://arxiv.org/abs/2304.09848)). Score both systems on the same items
    and analyze paired; log the discordance rate, since it, not n, is the real sample size.

## Push back on these

- **"More sources means more accuracy."** No. It means more tokens, and token usage alone explains
  80% of BrowseComp variance ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system))
  — spend is correlated with score, which is not the same as breadth causing correctness.
  Duplicate and syndicated sources actively harm accuracy by faking corroboration, and human
  testers found a systematic model preference for SEO content farms over authoritative sources
  ([same post](https://www.anthropic.com/engineering/multi-agent-research-system)). Fewer primary
  sources, verified, beats more secondary sources, cited.
- **"The citation list looks thorough."** A plausible-looking citation list is **the single most
  dangerous artifact this subsystem can produce.** It transfers the appearance of verification
  without the substance — the documented "facade of trustworthiness"
  ([arXiv 2304.09848](https://arxiv.org/abs/2304.09848)). Thoroughness of appearance is
  anti-correlated with scrutiny. Never treat citation count as a quality signal.
- **"The link resolves, so the citation is good."** That is Stage 1. Reachability is not support.
  Only the claim-support check is the gate.
- **"Let it keep refining until confidence is high."** An unbounded refinement loop is a cost
  incident, and the models' confidence calibration is documented as weak
  ([OpenAI](https://openai.com/index/introducing-deep-research/)). Cap iterations the way Forge's
  Document AI loop caps at 5, and terminate with an explicit not-found rather than a confident
  guess.
- **"Multi-agent is strictly better."** Anthropic lists where it is not: domains where all agents
  need the same context, tasks with many inter-agent dependencies, and most coding tasks
  ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Their own
  documented failures include spawning 50 subagents for a simple query.
- **"We can verify against the summarized notes to save tokens."** That verifies the summarizer.
  The 51.5% support failure happens at sentence level against source text; a summary-based check
  cannot observe it.
- **"An LLM judge score of 0.9 means the report is accurate."** Judges are biased in measured
  directions — GPT-4 shows only **65.0%** consistency under answer-order swap and a **+10%**
  self-preference on its own outputs, Claude-v1 **+25%**
  ([Zheng et al., arXiv 2306.05685](https://arxiv.org/pdf/2306.05685)). Use the judge for rubric
  quality, never as the citation gate. The gate is mechanical: fetch-log membership plus span
  entailment.

## Operator tasks — Jordan

Do not inline these into coding-agent steps. Living runbook:
`launch-plans/operator-pending-tasks.md`. All Fly changes via `fly secrets set`, never a deploy,
so rollback is a secret change.

1. **Research alias in `FORGE_LLM_MODELS`** on app `opensite-forge`. Give it its own alias with
   its own `timeout_secs` and `rps`. Do **not** raise `timeout_secs` on an existing shared chain:
   the effective overall deadline is `max(timeout_secs)` across the chain (config.rs:85-93,
   router.rs:678-686), and a large research timeout would starve fallbacks on unrelated routes —
   the same mechanism as the 2026-08-23 `DeadlineExceeded` storm. Current rebalanced values on the
   main chain are mistral `timeout_secs:90` and claude `150`; keep them.
2. **Cost-cap and fan-out env contract** (names are proposed, not from a doc — confirm against the
   implementation before setting):

   | Variable | Purpose |
   |---|---|
   | `FORGE_RESEARCH_ENABLED` | master switch; default off until the citation eval passes |
   | `FORGE_RESEARCH_MAX_TOTAL_TOKENS` | hard per-request token cap across planner, all subagents, and verifier |
   | `FORGE_RESEARCH_MAX_SUBAGENTS` | fan-out ceiling; must not exceed what `SCRAPE_BROWSER_POOL_SIZE=3` and `SCRAPE_TIER2_MAX_CONCURRENCY=2` can actually serve |
   | `FORGE_RESEARCH_MAX_ITERATIONS` | refinement cap; 5, matching the Document AI loop |
   | `FORGE_RESEARCH_MAX_FETCHES` | per-request fetch ceiling |
   | `FORGE_RESEARCH_VERIFIER_ALIAS` | the cheaper verification model alias |
   | `FORGE_RESEARCH_REPORT_ALIAS` | the long-context synthesis alias |
   | `FORGE_RESEARCH_ARTIFACT_PREFIX` | Tigris key prefix for reports and retained corpora |
   | `FORGE_RESEARCH_CORPUS_RETENTION_DAYS` | how long fetched text is retained; re-verification is impossible after it expires |

3. **Tigris bucket/prefix and lifecycle** for research artifacts and retained corpora, on the
   Encapsa Tigris account. Set the retention policy deliberately: retention length **is** the
   audit window, because re-verification needs the fetched text. Note `object_store` 0.14.1 has
   **no conditional delete** upstream, so do not build a lifecycle that assumes compare-and-delete.
4. **Per-vertical adapter credentials** (academic APIs, any licensed source) as Fly secrets on
   `opensite-forge`, with per-adapter rate limits recorded next to the key. Do not put a
   third-party research API key in the repo or in a template.
5. **Blocked on:** Phase 4B is unbuilt, and enabling `FORGE_RESEARCH_ENABLED` is **blocked on** the
   citation eval passing its exit criterion (every cited fact traces to a fetched source) on the
   ~20-query eval set. Unblocked by that gate, not by a date. Also blocked on a ruling for any new
   metric label class the subsystem needs (D-23a) — the label namespace is bounded by contract.
6. **Compliance register entry required** before first production traffic: research artifacts
   contain third-party content and must be covered by the same no-body-content-in-telemetry rule
   as Pack and Skill bodies, with `SENTRY_SEND_DEFAULT_PII` remaining `false`.

## Sources

- [Liu, Zhang & Liang — Evaluating Verifiability in Generative Search Engines (arXiv 2304.09848)](https://arxiv.org/abs/2304.09848)
  — the 51.5% sentence-support and 74.5% citation-support audit of four commercial systems; the
  baseline any citation gate must beat.
- [Gao et al. — ALCE (arXiv 2305.14627)](https://arxiv.org/abs/2305.14627) — automatic citation
  evaluation over fluency, correctness, and citation quality; best models lack complete support
  50% of the time on ELI5.
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  — orchestrator-worker architecture, +90.2% and ~15x token numbers, BrowseComp variance
  decomposition, effort-scaling heuristics, documented failure modes, context-budget and
  external-artifact patterns, judge rubric separating factual from citation accuracy.
- [OpenAI — Introducing deep research](https://openai.com/index/introducing-deep-research/)
  — end-to-end RL training over browsing, 5–30 minute task durations, and the explicit
  hallucination and weak-calibration limitations.
- [Shao et al. — STORM (arXiv 2402.14207)](https://arxiv.org/abs/2402.14207) — pre-writing stage,
  perspective discovery, FreshWiki results (+25% organized, +10% coverage), and the source-bias-
  transfer and over-association failure modes.
- [Tam et al. — format restriction and reasoning (arXiv 2408.02442)](https://arxiv.org/abs/2408.02442)
  — constrained decoding measurably degrades reasoning; relevant to structured report emission.
- [Zheng et al. — MT-Bench / LLM-as-judge (arXiv 2306.05685)](https://arxiv.org/pdf/2306.05685)
  — judge agreement 85%, position-bias consistency 65.0%, self-preference +10%/+25%; why the judge
  is not the citation gate.
