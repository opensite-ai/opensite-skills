# Citation verification protocol

The two-stage procedure, the hard-fail matrix, and the test shapes for Forge's Phase 4B research
subsystem. Companion to `../SKILL.md`. Read this before implementing or reviewing the verification
pass.

**Provenance of this document:** the measured failure rates and the rubric split are sourced and
linked. The two-stage procedure, the verdict taxonomy, and the hard-fail matrix are **not from a
doc** — no fetched source documents a production hard-fail citation gate. They are derived from the
measured failure rates below and are design guidance.

## Why a gate rather than a score

| Measurement | Value | Source |
|---|---|---|
| Generated sentences fully supported by their citations, avg. over 4 commercial generative search engines | **51.5%** | [arXiv 2304.09848](https://arxiv.org/abs/2304.09848) |
| Citations that support their associated sentence | **74.5%** | [arXiv 2304.09848](https://arxiv.org/abs/2304.09848) |
| Best models lacking complete citation support on ELI5 | **50% of the time** | [ALCE, arXiv 2305.14627](https://arxiv.org/abs/2305.14627) |
| OpenAI Deep Research stated limitations | hallucinates facts, fails to distinguish authoritative from rumor, **weak confidence calibration**, often fails to convey uncertainty | [OpenAI](https://openai.com/index/introducing-deep-research/) |

At a ~50% sentence-support rate, an advisory score is a rounding error on the reader's workload:
they still have to check every sentence. The only design that changes the reader's position is one
where an unsupported sentence cannot be emitted. Hence: gate, hard-fail, and prefer `n.a.` to an
unsupported value.

Anthropic's production rubric already separates the two properties that must be checked
separately — **factual accuracy** ("do the claims match the sources?") and **citation accuracy**
("do the cited sources match the claims?") — alongside completeness, source quality (primary over
secondary), and tool efficiency ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).

---

## Data structures

Two append-only records per request. Both are inputs to verification; neither is optional.

### Fetch log (the ground truth)

One entry per `fetch`, appended by the source adapter, never by the model.

```json
{
  "doc_id": "b3:9f2c...",
  "requested_url": "https://example.org/a",
  "final_url": "https://example.org/a?utm=x",
  "canonical_url": "https://example.org/a",
  "http_status": 200,
  "tier": "tier1",
  "content_hash": "b3:9f2c...",
  "fetched_at": "2026-08-25T21:14:03Z",
  "published_at": null,
  "content_bytes": 48213,
  "extractor": "dom_smoothie",
  "robots_verdict": "allowed",
  "ssrf_verdict": "allowed",
  "dedup_alias_of": null
}
```

Rules:

- `doc_id` is the `blake3` content hash. Two URLs with identical content collapse to one `doc_id`
  with an alias list; the citation still resolves through the alias.
- `published_at` is `null` unless the adapter obtained it structurally. Never infer a date from
  page text.
- A `fetch` that failed still gets an entry, with its status. Absence of an entry means the fetch
  never happened, which is what makes Stage 1 mechanical.
- The retained extracted text is stored content-addressed by `doc_id`, for at least
  `FORGE_RESEARCH_CORPUS_RETENTION_DAYS`. Verification and re-verification read it, not a summary.

### Claim record (the unit of verification)

```json
{
  "claim_id": "c-0031",
  "text": "Philter reported 99.46% recall on 2,000 UCSF notes.",
  "citations": [
    {"doc_id": "b3:9f2c...", "char_start": 18422, "char_end": 18790}
  ],
  "numerics": [{"kind": "percent", "value": 99.46}, {"kind": "count", "value": 2000}],
  "verdict": "supported",
  "verifier_alias": "research-verify",
  "verifier_score": 0.94,
  "checked_at": "2026-08-25T21:19:44Z"
}
```

A claim with zero citations is only legal if it is explicitly typed as non-factual (framing,
transition, or a stated inference marked as such). Everything else with no citation is
`unresolvable`.

---

## Stage 1 — existence and reachability

Cheap, mechanical, necessary, and **not the gate**.

1. **Fetch-log membership.** The citation's `doc_id` must exist in this request's fetch log. Not
   in a cache, not in a prior request, not on the open internet. This is the check that
   mechanically eliminates fabricated links — a model cannot invent a `blake3` hash of content it
   never received.
2. **Status.** The entry's `http_status` is 2xx and `content_bytes > 0`.
3. **Span validity.** `0 <= char_start < char_end <= len(retained_text[doc_id])`.
4. **Policy verdicts.** `robots_verdict == "allowed"` and `ssrf_verdict == "allowed"`. A document
   fetched in violation of either is a bug in the adapter, and a claim citing it must not ship.
5. **Alias resolution.** If the `doc_id` was deduplicated, resolve to the canonical `doc_id` and
   remap the span. A dedup pass that breaks a citation is a Stage 1 failure, not an acceptable
   loss.

Stage 1 does **not** look at the claim text. It cannot: a reachable, well-formed, topically
adjacent citation passes Stage 1 perfectly while failing to support the sentence — which is
precisely the documented 51.5% failure ([arXiv 2304.09848](https://arxiv.org/abs/2304.09848)).

---

## Stage 2 — claim support (the real gate)

### Procedure

1. **Decompose** the draft into atomic claims at sentence granularity or finer. Sentence level is
   the minimum, because sentence-level support is where the 51.5% failure is measured. A paragraph
   is not a claim.
2. **Bind** each claim to its `(doc_id, char_start, char_end)` span, resolved via Stage 1.
3. **Load the fetched span from the retained corpus.** Not a summary. Not the subagent's notes. Not
   a re-fetch. If the span exceeds the verifier's context, **split the span and require at least
   one sub-span to entail** the claim. Never compress; a summarize-then-verify pipeline verifies
   the summarizer.
4. **Run the entailment / faithfulness check.** Premise = fetched span. Hypothesis = claim text.
   Single verifier call, single prompt, emitting a 0.0–1.0 score plus a categorical verdict —
   Anthropic found that after testing multiple judges per component, **a single LLM call with a
   single prompt** was the most consistent and best aligned with human judgment
   ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). Do not
   ensemble; do not use the report model as its own verifier.
5. **Run the numeric and entity fidelity check separately, and mechanically.** Every figure, date,
   percentage, unit, and proper name in the claim must appear verbatim in the span, or be
   arithmetically derivable from values in the span. Derived values must be labeled derived and
   show their inputs. This is a string/arithmetic check, not a model call — entailment scoring is
   too tolerant of a transposed digit or a swapped unit, and this is the highest-frequency real
   error class in cited reports.
6. **Assign a verdict** from the taxonomy below. Only `supported` may ship as a cited assertion.
7. **Record** verdict, score, verifier alias, and span for every claim, supported or not. The
   dropped claims are the audit trail that the gate ran.

### Verdict taxonomy

| Verdict | Meaning | Action |
|---|---|---|
| `supported` | span entails the claim; all numerics and entities check | emit with citation |
| `partially_supported` | span entails part of the claim, or one of several numerics fails | rewrite to the supported subset and re-verify, or drop. Never emit as-is with a hedge. |
| `unsupported` | span does not entail the claim | drop the claim; emit `n.a.` if the report structure requires the slot |
| `unresolvable` | no citation, citation not in the fetch log, invalid span, or corpus expired | hard-fail the claim; if it appears at all, hard-fail the request |
| `policy_blocked` | cited doc has a failing `robots_verdict` or `ssrf_verdict` | drop the claim and raise an adapter bug |

`partially_supported` is where implementations leak. The tempting behaviour is to emit the claim
with a softening qualifier. That reproduces the 51.5% number with better manners. Rewrite or drop.

### What Stage 2 does not catch

STORM's expert reviewers identified two failure modes that survive per-claim entailment: **source
bias transfer** and **over-association of unrelated facts**
([arXiv 2402.14207](https://arxiv.org/abs/2402.14207)). Both produce reports where every claim is
individually entailed and the whole is misleading. Entailment is a floor. The mitigations are
report-level, not claim-level: require source diversity in the plan, prefer primary sources, and
keep a rubric-scored quality pass (separate from the gate) that looks at the synthesis rather than
the sentences.

Also do not use the rubric judge as the gate. Judges are biased in measured directions — GPT-4
shows **65.0%** consistency under answer-order swap (favoring the first position 30.0% of the
time) and a **+10%** self-preference for its own outputs, Claude-v1 **+25%**
([arXiv 2306.05685](https://arxiv.org/pdf/2306.05685)). The gate must stay mechanical: fetch-log
membership plus span entailment plus numeric fidelity.

---

## Hard-fail matrix

Request-level outcomes. `partial` means a report is emitted, explicitly marked partial, containing
only `supported` claims.

| Condition | Claim outcome | Request outcome |
|---|---|---|
| Citation `doc_id` absent from fetch log | drop | **hard-fail the request** — indicates fabrication or a broken adapter contract |
| Citation span invalid or out of range | drop | **hard-fail** — offset math bug; do not ship past it |
| Retained corpus expired or missing for a cited `doc_id` | drop | **hard-fail** — the report is unverifiable by construction |
| Cited doc has failing `robots_verdict` or `ssrf_verdict` | drop | **hard-fail** and raise an adapter bug |
| `unsupported` verdict on a factual claim | drop claim | continue; `partial` if any dropped |
| `partially_supported` and rewrite fails re-verification | drop claim | continue; `partial` |
| Every claim in a required report section drops | section becomes explicit `n.a.` | `partial`, with the section named |
| Verifier call fails or times out | claim is `unresolvable` | **hard-fail** — an unrun gate is a failed gate, never a pass |
| Numeric check fails while entailment passes | drop claim | continue; `partial`. Log it separately — a rising rate here means the report model is paraphrasing figures. |
| Cost cap reached mid-run | claims already verified stand | **partial**, marked; never an over-cap completion, never an unverified partial |
| Iteration cap reached with no answer | no claims | emit an explicit not-found report; never an invented answer |
| Structured emit unavailable (`capability_not_supported`, no fallback for `generate_structured` per D-9/D-26) | claims stand | degrade to unconstrained emit **plus** a schema validator; do not hard-fail the whole report on the emit format |
| Zero claims survive | — | **hard-fail** rather than emit an empty report styled as a finding |

Two asymmetries to keep straight: a **claim** failing support is normal operation (drop and
continue), while a **mechanism** failing — missing fetch log entry, invalid span, dead verifier,
expired corpus — is a request-level hard fail, because it means the gate did not actually run.

---

## Test shapes

Write these as tests, not as a review checklist. Assert on the emitted artifact, not on log lines.

### T1 — fabricated URL

Inject into the synthesis stage a citation to a plausible URL never present in the fetch log.
Expect: Stage 1 rejects, verdict `unresolvable`, request hard-fails, and the URL appears **nowhere**
in the artifact.

```rust
// shape only
let mut draft = draft_with_claim("Forge uses X.", cite("https://example.org/never-fetched"));
let out = verify(&draft, &fetch_log, &corpus);
assert!(matches!(out, Err(VerifyError::UnresolvableCitation { .. })));
```

### T2 — topically related but unsupported

Fetch a real document, then author a claim on the same topic that the document does not entail.
Expect: Stage 1 passes, Stage 2 returns `unsupported`, claim dropped, report marked `partial`. This
is the single most important test in the suite — it is the documented 51.5% failure shape, and a
pipeline that emits this claim has no gate regardless of what else it does.

### T3 — summary substitution refused

Configure the verifier to read a summary of the document instead of the span. Expect: the harness
refuses to run, or the test fails. This test exists solely to stop the shortcut from being
reintroduced during a token-cost optimization pass.

### T4 — numeric perturbation

Take a `supported` claim containing a figure and perturb one digit (`99.46` -> `99.64`), one unit
(`%` -> percentage points), and one date (year off by one), as three cases. Expect: `unsupported` in
all three. If entailment alone passes any of them, the mechanical numeric check is missing.

### T5 — derived arithmetic

Author a claim whose value is arithmetically derivable from two values in the span. Expect:
`supported`, with the claim carrying a derived label and its inputs. An unlabeled derived value
must fail.

### T6 — dedup does not break citations

Fetch two URLs with identical content, cite the one that gets aliased away. Expect: the citation
resolves through the alias to the canonical `doc_id` with a remapped span, verdict `supported`.

### T7 — span split on long documents

Cite a span longer than the verifier's context. Expect: the span is split, at least one sub-span
entails, verdict `supported` — and no summarization occurred anywhere in the path.

### T8 — cost cap

Set `FORGE_RESEARCH_MAX_TOTAL_TOKENS` below the planned fan-out cost. Expect: the governor
terminates, every claim in the emitted report is `supported`, the report is marked `partial`, and
total tokens counted across planner, subagents, and verifier are at or below the cap.

### T9 — iteration cap

Ask a question with no answerable source (the documented "endless searching for nonexistent
sources" failure, [Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)).
Expect: termination at `FORGE_RESEARCH_MAX_ITERATIONS` (5, matching the Document AI loop) with an
explicit not-found report.

### T10 — SSRF and robots

Have the planner emit `http://169.254.169.254/`, a Fly 6PN `.internal` host, and a
`robots.txt`-disallowed path. Expect: all three rejected by `src/scraping/ssrf.rs` and `robots.rs`
**before** any fetch, each rejection recorded in the fetch log with its verdict, and no claim able
to cite them.

### T11 — offline re-verification

Re-run verification over a stored artifact and its retained corpus with network access disabled.
Expect: byte-identical verdicts. If it cannot run offline, the corpus was not retained and the
artifact is not auditable. Run this in CI against a checked-in fixture artifact.

### T12 — audit completeness, both directions

Expect: every URL in the artifact appears in the audit record's fetched-source list, **and** the
audit record contains zero body content (matching Forge's metadata-only audit invariant and the
`SENTRY_SEND_DEFAULT_PII=false` rule). Assert the second direction with a content-substring scan,
not by inspection.

### T13 — verifier unavailable

Force the verifier alias to fail. Expect: request hard-fails. An unrun gate must never be a pass.

### T14 — eval set metrics

On a ~20-query eval set — the size Anthropic found already informative
([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)) — report:

| Metric | Definition | Target |
|---|---|---|
| Sentence-level support rate | fraction of emitted sentences whose citations entail them, human-audited | must exceed the 51.5% commercial baseline by a wide margin; the gate should make it ~100% by construction, so anything below that is a gate bug |
| Citation-support rate | fraction of citations that support their sentence | same |
| Drop rate | claims dropped by the gate / claims proposed | a rising drop rate is a report-model quality signal, not a gate problem |
| Numeric-failure rate | claims failing the numeric check while passing entailment | should trend to zero; a rise means the model is paraphrasing figures |
| Tokens per request | across planner, subagents, verifier | compare against the ~15x-chat multiplier baseline ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)) |
| Unresolvable rate | mechanism failures per request | must be zero in steady state; any nonzero value is a bug, not noise |

Score both the old and new pipeline on the **same** items and analyze paired; log the discordance
rate, since discordance, not n, is the real sample size for a comparison at this scale.

---

## Sources

- [Liu, Zhang & Liang, arXiv 2304.09848](https://arxiv.org/abs/2304.09848) — the 51.5% sentence-
  support and 74.5% citation-support audit; the baseline this protocol exists to beat.
- [Gao et al., ALCE, arXiv 2305.14627](https://arxiv.org/abs/2305.14627) — automatic citation
  evaluation and the ELI5 50%-incomplete-support result.
- [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
  — single-call judge finding, the factual-vs-citation-accuracy rubric split, the ~15x token
  multiplier, the ~20-query eval-set size, and the documented endless-search failure mode.
- [OpenAI — Introducing deep research](https://openai.com/index/introducing-deep-research/)
  — stated hallucination and weak-calibration limitations that motivate preferring `n.a.`.
- [Shao et al., STORM, arXiv 2402.14207](https://arxiv.org/abs/2402.14207) — source bias transfer
  and over-association, the failure modes per-claim entailment does not catch.
- [Zheng et al., arXiv 2306.05685](https://arxiv.org/pdf/2306.05685) — judge position bias (65.0%
  swap consistency) and self-preference (+10% / +25%); why the judge is not the gate.
