---
name: enterprise-nl2sql-architecture
description: "Architecture and decision guidance for enterprise-grade, database-agnostic natural-language-to-SQL over client-owned Postgres, MSSQL, MySQL, Oracle, Snowflake, and BigQuery warehouses at hundreds-of-databases / tens-of-thousands-of-tables scale. Load when designing, reviewing, or debugging text-to-SQL, NL2SQL, schema linking, catalog/metadata harvesting, semantic-layer routing, SQLGlot qualify/transpile/lineage, EXPLAIN (TYPE VALIDATE), BigQuery dry run, LSH value indexes, candidate reranking, repair loops, confidence gating, refusal policy, or read-only execution sandboxes; or when someone quotes a Spider accuracy number, proposes grammar-constrained decoding as an anti-hallucination fix, treats SQLGlot as a validator, or asks to point an LLM at an uncurated 10k-table warehouse. Covers Spider 2.0, BIRD, BIRD-CRITIC, BEAVER, CHESS, CHASE-SQL, MCS-SQL, XiYan-SQL, ReFoRCE, LinkedIn SQL Bot, dbt MetricFlow, Cube, Cortex Analyst, STEF, xgrammar, and Calcite."
license: Apache-2.0
metadata:
  version: '1.0'
  author: encapsa-forge
---

# Enterprise NL2SQL Architecture

**Governing principle: the model chooses; deterministic code decides.** Authority lives in the
retrieval index, the query compiler, the validator, and the selector — never in the LLM. Every
published system that works in production moves authority out of the model; every other decision in
this skill follows from that.

## When to Use This Skill

- Designing or reviewing a subsystem that turns natural language into SQL against **client-owned**
  databases across Postgres, MSSQL, MySQL, Oracle, Snowflake, or BigQuery.
- A client has hundreds of databases and tens of thousands of tables, and someone proposes putting
  the schema in a prompt.
- Someone quotes a **Spider** number (85-91% EX) as evidence the product will work.
- Someone proposes **grammar-constrained decoding** (xgrammar/PICARD) as the fix for hallucinated
  identifiers.
- Someone treats **SQLGlot parsing** as validation, or ships without an engine-side dry run.
- Building the metadata catalog, harvesters, value index, join inference, or refresh jobs.
- Building the execution sandbox, RLS story, cost guards, or audit record.
- Defining production quality metrics, ambiguity handling, confidence gating, or the refusal path.
- Writing the customer-facing accuracy claim. Read `references/benchmarks-and-honest-limits.md`
  before you write a number down.

Reference files, and when to read each:

| File | Read when |
|---|---|
| `references/benchmarks-and-honest-limits.md` | Quoting any accuracy number, setting expectations, evaluating a vendor claim, or choosing a schema serialization format |
| `references/retrieval-and-catalog.md` | Building or debugging retrieval, harvesters, profiling, join inference, value index, or refresh cadence |
| `references/validation-ladder.md` | Implementing the compiler/validator, repair loop, candidate selection, production eval, ambiguity detection, or confidence gating |
| `references/safety-and-governance.md` | Connecting a client database, writing the sandbox, RLS, cost guards, injection defenses, PII masking, credential isolation, or the audit record |

## Honest Accuracy — read this before anything else

This is where these projects die: a team ships against a Spider-derived expectation, meets enterprise
reality, and loses stakeholder trust before the architecture gets a fair test.

| Benchmark | Result | Meaning |
|---|---|---|
| Spider 1.0 top | **91.2 EX** (MiniSeek, Nov 2 2023) ([Spider leaderboard](https://yale-lily.github.io/spider)) | Databases average **5.1 tables / 25.7 columns** ([BEAVER](https://arxiv.org/html/2409.02038v3)). A toy. |
| Spider 2.0, o1-preview code agent | **21.3%** vs 91.2% on Spider 1.0 and 73.0% on BIRD ([arXiv 2411.07763](https://arxiv.org/abs/2411.07763)) | 632 real enterprise workflow problems, >1,000-column databases, >100-line SQL ([Spider 2.0](https://spider2-sql.github.io/)) |
| Spider 2.0-Snow, ex-Spider-champions | DAIL-SQL+GPT-4o **2.20%**; CHESS+GPT-4o **1.28%**; DIN-SQL+GPT-4o **0.00%** ([Spider 2.0](https://spider2-sql.github.io/)) | The same pipelines scored 85-86% on Spider 1.0 |
| BIRD | Human **92.96% EX** vs top test **81.95** (AskData+GPT-4o) ([BIRD](https://bird-bench.github.io/)) | 95 databases, 33.4 GB, but only 6.8 tables / 72.5 columns per DB ([BEAVER](https://arxiv.org/html/2409.02038v3)) |
| BIRD-CRITIC (repair) | O3-Mini **38.87% Postgres**, **33.33% multi-dialect** ([arXiv 2506.18951v1](https://arxiv.org/html/2506.18951v1)) | Your repair loop's oracle fixes roughly a third of real issues. Cap retries. |
| **BEAVER — best enterprise proxy** | best **11.4%** (ReFoRCE + Claude-4.5-sonnet); **101.5 tables / 869.4 columns per DB**; **schema linking = 35.2% of errors** ([BEAVER](https://arxiv.org/html/2409.02038v3)) | Three private enterprise warehouses. Plan around this number. |

**The Spider → Spider 2.0 → BEAVER gradient is the enterprise reality tax, not noise.** Accuracy for
the *same* systems falls roughly 86% → 10-21% → 4-11%, and the benchmarks differ mainly in schema
size, metadata quality, and query length — not in required SQL features. ReFoRCE scores **62.9% on
Spider 2.0 and 11.4% on BEAVER** ([BEAVER](https://arxiv.org/html/2409.02038v3)). Do not model this
as something the next model generation erases.

The mitigations that move the needle are **retrieval quality, catalog-grounded validation, and
semantic-layer routing** — not better prompting. Self-consistency on Spider is worth **+0.4 points**
(86.2 → 86.6, [Spider leaderboard](https://yale-lily.github.io/spider)); knowledge-graph grounding
took GPT-4 from **16% to 54%** on an enterprise insurance schema
([arXiv 2311.07509](https://arxiv.org/abs/2311.07509)). That is the whole argument.

### Suspicion clause for the Spider 2.0-Snow top of the leaderboard

Entries above 90% (Genloop Sentinel 96.70, Native mini 96.53, QUVI-3 94.15, TCDataAgent 93.97, Prism
Swarm 90.49) must not be used as a target. From the site's own caveats
([Spider 2.0](https://spider2-sql.github.io/)): Spider 2.0-Snow "includes well-prepared database
metadata and documentation"; methods marked `-*` use ground-truth tables and are excluded from
ranking (oracle tables provided 2025-04-20); "scores may change slightly over time"; and **gold
answers have been public since 2024-12-24**, prompting a 2025-01-07 warning not to SFT on gold SQL.
Those numbers do not measure "can an agent find the right tables in a 10,000-table warehouse."

### Bands to quote a customer

| Configuration | Band |
|---|---|
| Raw schema, large warehouse | **10-30%** ([Spider 2.0](https://spider2-sql.github.io/), [BEAVER](https://arxiv.org/html/2409.02038v3)) |
| Retrieval + validation + candidate selection on a curated catalog | **n.a. for this exact configuration**; LinkedIn production reports **48-53% "good or better"** on its own 133-question benchmark ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)) |
| Governed semantic layer, in-scope questions | **90-100%** ([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026), [Snowflake](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)) |

## The 12-Step Request Path

1. **Tenant + credential resolution.** Per-(tenant, database) credential from a KMS-backed secret
   store, fetched by connection ID, **never rendered into a prompt or a log line**. Resolution
   happens before any model call. OWASP: "handle these functions in code rather than providing them
   to the model" ([OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)).
2. **Ambiguity gate.** Classify, then **ask rather than guess**. Google's canonical case: for "What
   is the best selling shoe?" ask "ordered by order quantity or revenue?", and orchestrate LLM
   calls to first determine whether the question is answerable from the available schema and data
   ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql),
   [arXiv 2508.15276v2](https://arxiv.org/html/2508.15276v2)). CLUES shows a two-axis
   ambiguity/instability score isolates **51% of errors in 25% of queries**
   ([ar5iv 2602.12015](https://ar5iv.labs.arxiv.org/html/2602.12015)).
3. **Semantic-layer route check — FIRST, before retrieval.** If the question maps to a modeled
   metric, answer through the compiler and stop. This is the **90-100% band**: dbt measured
   **90.0 → 98.2** (claude-sonnet-4-6) and **84.1 → 100.0** (gpt-5.3-codex) moving from text-to-SQL
   to the semantic layer ([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)),
   and lkr.dev measured Looker NL2LookML **97%** vs BigQuery NL2SQL **80%** on 44 questions × 3 runs
   ([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)).
   Harvest the client's existing semantic layer where one exists — Snowflake now exposes
   `SEMANTIC_VIEW`, `SEMANTIC_METRICS`, `SEMANTIC_DIMENSIONS`, `SEMANTIC_FACTS`,
   `SEMANTIC_RELATIONSHIPS` in INFORMATION_SCHEMA
   ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)).
4. **Hierarchical retrieval** (only if not routed): domain/cluster → **~20 tables** → rerank to
   **~7 without schemas in the ranker** → column filter. LinkedIn's parameters: ICA `N_comp = 200`,
   `T_c = 20` tables/cluster over 3 months of query history (job completes in **15 min at p90**),
   `K_ret = 20`, `K_rnk = 7`; including schemas in the table ranker **lowered recall and increased
   latency** ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
5. **Column filtering with PK/FK force-include.** Linking columns are always retained regardless of
   filter output, because PKs are needed for counting and FKs for joins and they often look
   semantically unrelated to the question
   ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)). CHESS's table-selection stage
   alone is worth **6.12%**.
6. **Literal grounding via an LSH value index.** Unique values LSH-indexed offline; at query time
   top-10 candidates refined by edit distance and embedding cosine similarity; per (keyword,
   column) keep only the smallest-edit-distance value. Measured **~5 min → ~5 sec**
   ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)). This is what stops
   `WHERE region = 'North America'` when the column stores `'NA'`.
7. **Diverse candidate generation.** CHASE-SQL's three generators — divide-and-conquer
   decomposition in a single call, chain-of-thought over query **execution plans**, and
   instance-aware synthetic exemplars — with retrieved exemplars
   ([arXiv 2410.01943](https://arxiv.org/abs/2410.01943),
   [arXiv 2308.15363](https://arxiv.org/abs/2308.15363)). Optionally constrain output *shape* with
   a SQL EBNF grammar via vLLM/xgrammar
   ([vLLM docs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)).
8. **The 7-rung validation ladder** (next section). Nothing skips it.
9. **Repair loop capped at 2 retries**, each fed the **complete** error list from catalog
   validation rather than one engine error at a time
   ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). CHESS's revision node is worth
   **6.80%** ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)); BIRD-CRITIC caps
   the expectation at ~33-39% of real issues fixed
   ([arXiv 2506.18951v1](https://arxiv.org/html/2506.18951v1)).
10. **Sandboxed execution.** Read-only role + read-only transaction + `statement_timeout` +
    `lock_timeout` + `idle_in_transaction_session_timeout` + safety `LIMIT` + bytes-billed cap +
    RLS with `FORCE ROW LEVEL SECURITY` and no `BYPASSRLS`
    ([PostgreSQL client config](https://www.postgresql.org/docs/current/runtime-config-client.html),
    [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html),
    [BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)).
11. **Selection over EXECUTED candidates.** Pairwise fine-tuned selector plus result-set agreement
    ([arXiv 2410.01943](https://arxiv.org/abs/2410.01943),
    [arXiv 2405.07467](https://arxiv.org/abs/2405.07467)). Never select over strings — string-level
    voting is worth +0.4 points ([Spider leaderboard](https://yale-lily.github.io/spider)).
12. **Confidence gate that refuses**, then an **audit record with column-level lineage** from
    SQLGlot `lineage()` ([SQLGlot lineage](https://sqlglot.com/sqlglot/lineage.html)). dbt's
    operational point is the one to adopt system-wide: text-to-SQL "fails silently" with plausible
    wrong numbers, a semantic layer "fails loudly" by refusing
    ([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)). A product that
    cannot refuse is strictly worse than one that can, independent of mean accuracy.

Two published stages were **measured and rejected** — do not build them: an extra "approach
generation" LLM call did not improve recall, and a query-planner LLM added latency, over-nested the
queries, and *lowered* recall and quality ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

## The 7-Rung Validation Ladder

Cheapest first. Each rung catches a distinct failure class. A candidate clears all seven or it is
not a candidate. Full code shapes and per-dialect specifics in
`references/validation-ladder.md`.

| Rung | Check | Mechanism |
|---|---|---|
| 1 | **Parse** in the target dialect | `sqlglot.parse_one(sql, read=dialect)`; surface all of `ParseError.errors` (description, line, col, start_context, highlight, end_context) ([SQLGlot docs](https://sqlglot.com/sqlglot.html)) |
| 2 | **AST statement allowlist** | Assert root is `Select`; reject `Insert/Update/Delete/Drop/Create/Alter/TruncateTable/**Command**` anywhere in the tree, including inside CTEs. `exp.Command` is where unmodeled statements hide. Usability guard, **not** a security boundary |
| 3 | **`qualify` against the catalog** | `qualify(ast, dialect=…, schema=catalog_slice, validate_qualify_columns=True, allow_partial_qualification=False, infer_schema=False)` ([SQLGlot qualify](https://sqlglot.com/sqlglot/optimizer/qualify.html)). This is the anti-hallucination rung, and it needs no database |
| 4 | **Dialect transpile** | `transpile(..., unsupported_level=sqlglot.ErrorLevel.RAISE)`. Without `RAISE`, unsupported translations only **warn** ([SQLGlot docs](https://sqlglot.com/sqlglot.html)) |
| 5 | **Engine dry-run** | Trino `EXPLAIN (TYPE VALIDATE) <stmt>` returns `Valid \| true` and precise messages (`line 1:15: Table 'tpch.tiny.nations' does not exist`) ([Trino EXPLAIN](https://trino.io/docs/current/sql/explain.html)); BigQuery **dry run** validates and estimates bytes, uses no slots and incurs no charges ([BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)); Postgres/MySQL/MSSQL/Oracle/Snowflake via `PREPARE`/`EXPLAIN` in an aborted read-only transaction — **exact per-engine no-execute semantics n.a., verify each** |
| 6 | **Independent catalog hallucination check** | Set-check every extracted table and column against the index. LinkedIn runs EXPLAIN VALIDATE **at most twice** *plus* a separate index validator, specifically because "Trino EXPLAIN returns one error at a time" ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)) |
| 7 | **Researcher/repair dispatch** | Similarity-search the catalog for tables near the hallucinated ones (LinkedIn uses gpt-4o-mini) ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)) |

Rungs 5 and 6 are not redundant. Engine validation is a **serial oracle** — one error per round
trip. Catalog validation is a **set operation** — every bad identifier in one pass. The repair loop
needs the set, or it burns its 2-retry budget one error at a time.

Google's guidance corroborates the whole ladder: "non-AI techniques, including query parsing and
dry runs of generated SQL, complement model-based workflows… providing a clear, deterministic
signal when the LLM has missed something crucial"
([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).

**Pin rung 3's exception in a test.** The exact exception class raised for an unresolvable column is
**n.a.** on the qualify docs page; determine it empirically and treat a SQLGlot upgrade that changes
it as a breaking change.

## Three Positions to Hold Under Pushback

### 1. Do not ship raw text-to-SQL against an uncurated 10k-table warehouse

The same pipelines that score **85-86% on Spider 1.0** score **0.00-2.20% on Spider 2.0-Snow** and
**3.6-5.1% on BEAVER** ([Spider leaderboard](https://yale-lily.github.io/spider),
[Spider 2.0](https://spider2-sql.github.io/), [BEAVER](https://arxiv.org/html/2409.02038v3)). Quote
DIN-SQL: 85.3 on Spider, **0.00%** on Spider 2.0-Snow. If the counter-argument is "The Death of
Schema Linking?" ranking first on BIRD at 71.83%
([arXiv 2408.07702](https://arxiv.org/abs/2408.07702)), the reply is that its stated precondition is
"the schema fits the context window," and BIRD databases average **6.8 tables**
([BEAVER](https://arxiv.org/html/2409.02038v3)). That precondition is exactly what fails here.

### 2. Grammar-constrained decoding is not the anti-hallucination answer

xgrammar genuinely supports full CFGs including **left recursion** (`root ::= root "a" | "a"` is a
documented working example), with `?`/`*`/`+`/`{n,m}` repetition, forward references, per-rule
`max_tokens`/`max_chars` budgets, and macros
([XGrammar EBNF docs](https://xgrammar.mlc.ai/docs/defining_structures/ebnf_grammar.html)), and
vLLM documents SQL as a grammar target — EBNF support "allows users to define complete languages
such as SQL queries," shipping a `simplified_sql_grammar` example
([vLLM docs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)). None of that helps
with identifiers: **a CFG cannot express "this column belongs to a table in scope."** You could
compile a per-request grammar enumerating retrieved identifiers as literal alternatives, which
would make identifier hallucination structurally impossible, but you pay compilation cost per
request and it still cannot constrain correlated usage (right column, wrong table's alias).

**Catalog-based identifier resolution is the answer.** LinkedIn drove schema hallucination from
**23% to 1%** with rankers, validation, and a fixer — not with a grammar
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Use grammar for shape, `qualify` for
identifiers, execution for semantics.

### 3. Do not treat SQLGlot as a validator

Its own docs, verbatim: "The parser is intentionally lenient. It can accept queries that a real
engine would reject. SQLGlot is a transpiler, not a validator. A query that parses successfully may
still fail at execution time." ([SQLGlot docs](https://sqlglot.com/sqlglot.html)) What you need is
`qualify(..., schema=catalog_slice, validate_qualify_columns=True)`
([SQLGlot qualify](https://sqlglot.com/sqlglot/optimizer/qualify.html)) **plus** an engine-side dry
run. If in-process rigor equal to an engine is genuinely required, the escalation path is Apache
Calcite, whose parser, validator, and optimizer are all complete — at the cost of modeling every
client schema into a Calcite `Schema`/`Table` and running on the JVM
([Calcite docs](https://calcite.apache.org/docs/)).

## Offline Catalog Path

Details and per-engine caveats in `references/retrieval-and-catalog.md`.

- **Per-dialect harvesters into one normalized catalog.** INFORMATION_SCHEMA is not a portable API:
  Oracle has none (use `ALL_TAB_COLUMNS`; `ALL_*`/`DBA_*`/`USER_*` differ, and `ALL_TAB_COLUMNS`
  filters hidden columns while `ALL_TAB_COLS` does not,
  [Oracle docs](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html));
  SQL Server's views had changes that "break backward compatibility"
  ([Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/system-information-schema-views/system-information-schema-views-transact-sql?view=sql-server-ver17));
  Snowflake's are role-dependent, subject to change, error out on unselective filters, and need a
  running warehouse ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)).
- **Carry per node:** structure, **Human Description, AI Description, Usage Popularity, Table
  Cluster, Certification/Deprecation Status, Top Values, Is Partition Key** — LinkedIn's published
  attribute set, sourced from DataHub metadata, query logs, wikis, code repos, jargon glossaries,
  and crowdsourced domain knowledge ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
- **Profile from optimizer statistics, not table scans.** Oracle's `NUM_DISTINCT`, `NUM_NULLS`,
  `LOW_VALUE`, `HIGH_VALUE`, `DENSITY` are already computed by `DBMS_STATS`
  ([Oracle docs](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html)).
  A profiling scan on a client production warehouse is an availability incident you caused.
- **Infer joins from parsed query logs and EXPLAIN plans.** LinkedIn parses Trino EXPLAIN plan JSON
  for fully-qualified tables, columns, and **join conditions**
  ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)); elsewhere parse historical SQL with
  SQLGlot and walk the AST, using `lineage()` for provenance through views and CTEs
  ([SQLGlot lineage](https://sqlglot.com/sqlglot/lineage.html)). Inferred-join accuracy evidence is
  **n.a.** — treat them as suggestions with confidence, require human certification, and never let
  one reach a governed metric.
- **LSH value index**, refreshed independently of the structural catalog
  ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).
- **Refresh: weekly structural, weekly usage, weekly cluster; example queries as-needed; domain
  knowledge instant** ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Snowflake
  INFORMATION_SCHEMA gives **no consistency guarantee under concurrent DDL**, so version the catalog
  and let validation be the query-time authority; and Snowflake `QUERY_HISTORY` retains only **7
  days** (most other history functions 14 days), so copy the query log out at least that often or
  the join-inference corpus is gone
  ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)).
- **Continuous synthetic multi-dialect benchmark**, because academic benchmarks "can lack broad
  real-world schemas and workloads"
  ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).

## Safety and Governance

Full detail in `references/safety-and-governance.md`. The invariants:

- **Read-only role** (the only real boundary) + **read-only transaction** via
  `default_transaction_read_only` set per-session, not in `postgresql.conf`
  ([PostgreSQL docs](https://www.postgresql.org/docs/current/runtime-config-client.html)).
- **`statement_timeout` and `lock_timeout` set explicitly.** Zero is the `statement_timeout` default
  and **disables it**; `lock_timeout` is pointless at or above it; add
  `idle_in_transaction_session_timeout` because you hold a read-only transaction across the repair
  loop ([PostgreSQL docs](https://www.postgresql.org/docs/current/runtime-config-client.html)).
- **Safety `LIMIT`** unless the question implies an unbounded listing; STEF recommends **λ_min = 1000** ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)).
- **Bytes-billed cap** plus a BigQuery dry run for the pre-execution estimate, which uses no slots and
  incurs no charges ([BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)).
- **`FORCE ROW LEVEL SECURITY`, and no `BYPASSRLS`.** Superusers and `BYPASSRLS` roles "always bypass
  the row security system," and table owners bypass it too without `FORCE`
  ([PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)). RLS equivalents
  for MSSQL/MySQL/Oracle VPD/Snowflake/BigQuery are **n.a.** — verify before enabling that dialect
  for a row-restricted tenant.
- **Prompt-injection exposure per [OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).**
  Column comments, descriptions, and *cell values* enter your prompts; the value index injects
  customer-controlled data by design ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).
  Fence untrusted content in a delimited block ("Separate and clearly denote untrusted content"),
  validate output with deterministic code, keep credentials in code only. OWASP notes RAG and
  fine-tuning "do not fully mitigate" injection — design for injection succeeding at the prompt
  layer and failing at every layer below.
- **PII masking before the value enters a prompt**, driven by a per-column sensitivity attribute in
  the catalog. Sensitive columns contribute type and cardinality to retrieval, never values.
- **Per-tenant credential isolation:** one KMS-backed credential per (tenant, database), fetched by
  connection ID, never in a prompt or log; tenant-partitioned retrieval index, since table and column
  names are confidential. **Harvest with the same role you query with** — Snowflake's catalog output
  varies by role ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)).
- **Audit record** retains question, retrieved schema slice, all candidate SQL, per-rung validation
  results, chosen SQL, engine, executing role, row count, bytes/slots, latency, confidence, and
  **column-level lineage** ([SQLGlot lineage](https://sqlglot.com/sqlglot/lineage.html)). Handle its
  three documented `SqlglotError` strings, including "Cannot fetch lineage for unnamed projection" —
  require aliases on computed projections at generation time.

## Production Evaluation and Confidence Gating

No gold SQL exists in production. Measure anyway.

- **STEF** requires no gold SQL, no schema, and no execution: **Φ = (B/10) × 100 × Γ** over filter
  and verdict sub-scores with a confidence multiplier, thresholds **90-100 Excellent (automated
  production use) / 75-90 Good / 50-75 Marginal (escalate) / <50 Poor**
  ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)); full scoring rubric in
  `references/validation-ladder.md`. Two caveats to state every time: human-agreement correlation is
  **n.a.**, and the authors concede it **degrades on deeply nested subqueries and window functions**
  — exactly this product's target query class.
- **Deterministic proxies on 100% of traffic:** successful compilation rate and valid
  tables/columns rate. LinkedIn: **96%** and **99%** full config vs **88%** and **77%** in ablations
  ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). No judge, no gold SQL, and they move
  the instant retrieval or validation regresses. Alert on them.
- **Ambiguity detection is an accuracy feature, not UX polish.** CLUES's two-axis
  ambiguity/instability score isolates **51% of errors in 25% of queries**
  ([ar5iv 2602.12015](https://ar5iv.labs.arxiv.org/html/2602.12015)); AmbiSQL, AMBROSIA, AmbiQT, and
  PRACTIQ are the inventory (see `references/validation-ladder.md`).
- **Confidence gate composes four signals:** hard catalog-validity gate (target the published 99%
  valid-tables/columns rate), candidate result-set agreement, STEF Φ against its thresholds, and the
  ambiguity score. Below the gate, refuse and escalate. Do not soften the refusal into a hedged
  answer.

## Non-negotiables

1. **No SQL executes unless every identifier resolved against the harvested catalog** (rung 3) and
   the engine accepted it without executing (rung 5).
2. **The model never sees a credential, a connection string, or a catalog wider than its retrieved
   slice.**
3. **The read-only database role is the security boundary.** The AST allowlist is a usability guard.
   Never invert that.
4. **Repair retries capped at 2**, each fed the complete error list.
5. **Selection happens over executed candidates only.** Never over strings.
6. **The system can refuse.** A confidence gate with no refusal path is not a gate.
7. **No Spider number appears in any customer-facing or internal accuracy claim.** BEAVER is the
   proxy; state the band and the configuration.
8. **Per-tenant partitioning of catalog, value index, credentials, and audit.** No shared index.
9. **Inferred joins never reach a governed metric** without human certification.
10. **Marked-`n.a.` facts are never asserted.** Verify empirically and pin a test, or say
    "unverified — measure it."
11. **Compliance tests are non-waivable.** PHI must never reach a non-HIPAA-eligible provider.
12. **Fallback-first, and the fallback must be reachable.** Note the standing Forge sharp edge: the
    effective overall deadline behaves as `max(timeout_secs)` across the chain
    (`config.rs:85-93` + `router.rs:678-686`), so a slow first provider starves the fallback.

## Verification

Prove the work with these, not with "make sure it works."

**Validator conformance, per dialect (six dialects, three assertions each):**

```python
STRICT = dict(validate_qualify_columns=True, allow_partial_qualification=False,
              infer_schema=False)
for bad in ("SELECT 1 FROM no_such_table", "SELECT nope FROM orders"):
    with pytest.raises(Exception):            # narrow to the observed class, then pin
        qualify(sqlglot.parse_one(bad, read=d), schema={"orders": {"id": "INT"}}, **STRICT)
# engine-side: rejects an unknown table and materializes zero rows
assert engine_validate(d, "SELECT * FROM tpch.tiny.nations").ok is False
```

- **Statement allowlist:** a corpus containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`,
  `ALTER`, `TRUNCATE`, a `GRANT` (must be caught as `exp.Command`), and each of those nested inside
  a CTE. Every one rejected at rung 2.
- **Transpile strictness:** assert `UnsupportedError` is raised for a known-unsupported translation
  under `unsupported_level=ErrorLevel.RAISE`, and grep for any `transpile(` without
  `unsupported_level` in production paths.
- **Engine validate:** Trino `EXPLAIN (TYPE VALIDATE)` returns `Valid | true` on a good query and
  `line 1:15: Table '...' does not exist` on a bad one
  ([Trino EXPLAIN](https://trino.io/docs/current/sql/explain.html)); `bq query --dry_run` prints
  "Query successfully validated…", consumes **0** slots and **0** charge, and
  `total_bytes_processed` is compared against the bytes cap before submission
  ([BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)).
- **Sandbox guards:** an unbounded query aborts on `statement_timeout`; a lock-waiting query aborts
  on `lock_timeout`; an abandoned session is reaped by `idle_in_transaction_session_timeout`; a
  write attempt fails on the role privilege, *and separately* on the read-only transaction, *and
  separately* at rung 2 — assert all three independently, since each must hold alone.
- **RLS:** with the tenant role, a table with RLS enabled and no policy returns **zero rows**
  (default-deny); the role has neither superuser nor `BYPASSRLS`; and with `FORCE ROW LEVEL
  SECURITY` an owner-equivalent role is still filtered
  ([PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)).
- **Injection red-team fixtures:** poisoned column comment, poisoned cell value, description
  instructing a join to a PII table, description instructing a `GRANT`. Each yields a normal answer
  or a refusal, never a policy violation, and each is recorded in the audit log.
- **Credential hygiene:** grep every prompt payload and log line from a full integration run for the
  secret material; zero matches required, and the credential must resolve before the first model
  call in the trace.
- **Retrieval metrics on a held-out per-tenant question set:** table and column recall, with
  LinkedIn's **78% / 56%** as the reference point
  ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
- **Continuous production dashboards:** successful compilation rate (target ≥96%) and valid
  tables/columns rate (target ≥99%)
  ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)); mean and P90 STEF Φ with coverage
  ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)); refusal rate; retry-exhaustion rate.
  A drop in compilation or valid-identifier rate is a retrieval or catalog-staleness regression —
  page on it.
- **Catalog freshness:** assert a synthetic dropped column produces a **validation failure**, not a
  wrong answer, before the next weekly refresh.

## Mapping onto Forge

**All of this subsection is design guidance and "not from a doc" — no Forge doc currently specifies
this subsystem.** The Forge facts it builds on are verified; the placement is a proposal.

- It would be a **new Forge subsystem behind the existing HMAC-authenticated surface**. Forge uses
  two HMAC signing schemes: service routes sign `path:ts`, tenant routes sign
  `path:ts:tenant:caller:` (trailing colon significant). An NL2SQL route is a tenant route.
- Generation would be **routed through the `LlmRouter`**, so its guarantees and constraints apply to
  the generating model: `GuardrailProvider` wrapping inside `new_with_metrics` so no registration
  path bypasses the guardrail mode (`router.rs:112-117`), filter order
  **HIPAA → Provenance → Capability**, and construction-time config validation. **PHI gating and
  provenance filtering apply to the SQL-generating model.** Since every roster entry is
  `hipaa_eligible: false` until the RunPod BAA is signed (D-5), a PHI-tagged NL2SQL request fails
  closed with `PhiPolicy` — correct behavior, and a product constraint to state rather than route
  around.
- If the generator uses the structured/xgrammar path for grammar-constrained shape, note that
  **structured generation has no fallback**: `AnthropicProvider` returns terminal
  `capability_not_supported` for `generate_structured` (`anthropic.rs:218`) (D-9, D-26). Grammar
  constraints therefore cost you the fallback provider — weigh that against the fact that a CFG
  cannot prevent identifier hallucination anyway (position 2 above).
- **The catalog lives in Tigris object storage, not a Forge-owned database.** Cargo.toml states
  verbatim: "Forge is a stateless inference service — no direct DB dependency. DB writes … are the
  caller's responsibility." Tenant policy and context state already live in Tigris
  (`src/context/policy/tigris.rs`). `docs/ARCHITECTURE.md` still describes Postgres schemas and is
  **stale on this point** — trust the code and phase contract docs.
- **Connected client databases are reached only through per-tenant credentials**, resolved from the
  secret store at request time. Forge itself holds no standing connection to a client warehouse.
- Audit: Forge's existing audit records are **metadata only, never prompt/response content**, with
  caller identities as unsalted BLAKE3 digests (D-7) and raw tenant IDs (R-2C-H). An NL2SQL audit
  record must retain question text and SQL, so it does **not** fit the `forge_audit` stream as-is —
  it needs its own ruling and its own store.
- Metrics: the label taxonomy is a **bounded namespace by contract**; a new label value class needs
  a ruling, not a PR (D-23a). Per-dialect or per-tenant-database labels are exactly the unbounded
  cardinality that contract forbids — aggregate, or get a ruling first.
- Sequencing: **blocked on** a decision ruling for the audit store and the metric label class;
  **blocked on** per-dialect harvester and validator conformance suites; **unblocked** for catalog
  schema design and the SQLGlot validation ladder, both of which are pure-CPU work that fits Forge's
  Fly.io CPU tier.

## Operator Tasks — for Jordan

Do not inline these into coding-agent instructions.

1. **Secret store provisioning.** KMS-backed store for per-(tenant, database) credentials plus the
   Fly secret granting Forge read access. One credential per tenant database; no pooled account.
2. **Per-tenant database roles.** Per client database, request or provision a role that is not
   superuser, **not `BYPASSRLS`**, not the table owner, `SELECT`-only, and tolerant of session-level
   `default_transaction_read_only`. Record the role name in the connection registry.
3. **Client-side RLS confirmation.** For any tenant with row-level restrictions, get written
   confirmation that `FORCE ROW LEVEL SECURITY` is applied on the relevant tables and that no
   policy-free RLS-enabled table is expected to return rows.
4. **Snowflake query-log export.** Copy out `QUERY_HISTORY` at least every **7 days** (retention is
   7 days; most other history functions are 14)
   ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)). A missed window
   permanently loses join-inference and exemplar data.
5. **Snowflake harvest warehouse.** INFORMATION_SCHEMA needs a **running warehouse** — provision a
   small auto-suspend warehouse, and confirm the harvest role matches the execution role.
6. **BigQuery bytes-billed cap.** Set maximum-bytes-billed per tenant project. The API field name
   and CLI flag are **n.a.** from the fetched docs — confirm against the current reference first
   ([BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)).
7. **Tigris bucket for the catalog.** Bucket or prefix for the normalized catalog and LSH value
   index, tenant-partitioned by prefix, access keys installed as Forge secrets.
8. **Decision-register entries.** Open candidate decisions for (a) the NL2SQL audit store, since
   Forge audit is metadata-only by contract (D-7), and (b) the metric label class for dialect and
   tenant-database dimensions, given the bounded-namespace contract (D-23a). Record both in
   `project-meta/product-decision-register.md`; track operator items in
   `launch-plans/operator-pending-tasks.md`.
9. **Injection red-team sign-off.** Approve a per-tenant policy for whether poisoned metadata found
   in a client database is reported to the client, quarantined, or both.
10. **PHI posture.** Confirm whether any tenant's questions or schema slices are in PHI scope. If
    yes, the NL2SQL path is blocked on the RunPod BAA (D-5) and must fail closed until then.

## Sources

**Benchmarks and honest limits.** [Spider 1.0 leaderboard, Yale LILY](https://yale-lily.github.io/spider) — dataset scale, the 79.9-91.2 EX leaderboard, the +0.4 self-consistency delta. [Spider 2.0 project site](https://spider2-sql.github.io/) — Spider 2.0-Snow leaderboard, the 0.00-2.20% scores of ex-Spider champions, and the curated-metadata / oracle-table / gold-answer-release caveats. [Spider 2.0 paper, arXiv 2411.07763](https://arxiv.org/abs/2411.07763) — the 21.3% vs 91.2% vs 73.0% gap. [BEAVER, arXiv 2409.02038v3](https://arxiv.org/html/2409.02038v3) — 11.4% best, 101.5 tables / 869.4 columns per DB, schema linking at 35.2% of errors. [BIRD](https://bird-bench.github.io/) — human 92.96% EX vs top test 81.95, and R-VES. [BIRD-CRITIC, arXiv 2506.18951v1](https://arxiv.org/html/2506.18951v1) and its [repo](https://github.com/bird-bench/BIRD-CRITIC-1) — repair ceilings (O3-Mini 38.87% Postgres / 33.33% multi-dialect) and dialect splits.

**Architectures and methods.** [LinkedIn SQL Bot, arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1) — the production reference architecture: retrieval funnel parameters, the ablation table, hallucination 23%→1%, compilation 96%, valid tables/columns 99%, node attributes, refresh cadence, and the rejected planner/approach stages. [CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755) and [arXiv 2405.16755](https://arxiv.org/abs/2405.16755) — LSH value retrieval (~5 min → ~5 sec), three-stage schema selection, table selection +6.12%, revision node +6.80%, PK/FK force-include. [CHASE-SQL, arXiv 2410.01943](https://arxiv.org/abs/2410.01943) and [MCS-SQL, arXiv 2405.07467](https://arxiv.org/abs/2405.07467) — diverse candidate generation with pairwise / multiple-choice selection. [DAIL-SQL, arXiv 2308.15363](https://arxiv.org/abs/2308.15363) — question representation and exemplar selection. [XiYan-SQL, arXiv 2411.08599](https://arxiv.org/abs/2411.08599) and [M-Schema](https://github.com/XGenerationLab/M-Schema) — the multi-generator ensemble; serialized format and DDL comparison are n.a. ["The Death of Schema Linking?", arXiv 2408.07702](https://arxiv.org/abs/2408.07702) — the counter-argument, valid only when the schema fits the context window. [Knowledge graphs for enterprise text-to-SQL, arXiv 2311.07509](https://arxiv.org/abs/2311.07509) — GPT-4 at 16% raw vs 54% over an ontology.

**Validation tooling.** [SQLGlot docs](https://sqlglot.com/sqlglot.html) — 30+ dialects, and the governing caveat that the parser is lenient and SQLGlot is a transpiler, not a validator. [SQLGlot qualify](https://sqlglot.com/sqlglot/optimizer/qualify.html) — the identifier-resolution API and full signature. [SQLGlot lineage](https://sqlglot.com/sqlglot/lineage.html) — column-level lineage and its three error strings. [Trino EXPLAIN](https://trino.io/docs/current/sql/explain.html) — `EXPLAIN (TYPE VALIDATE)` semantics and error shapes. [BigQuery running queries](https://cloud.google.com/bigquery/docs/running-queries) — dry run validates with no slots and no charges, plus maximum-bytes-billed. [Apache Calcite](https://calcite.apache.org/docs/) — the real-validator escalation path. [Substrait](https://substrait.io/), [ADBC](https://arrow.apache.org/adbc/current/index.html), and [Trino use cases](https://trino.io/docs/current/overview/use-cases.html) — cross-engine IR, uniform catalog inspection, federation scope; maturity and driver coverage n.a.

**Constrained decoding.** [vLLM structured outputs](https://docs.vllm.ai/en/latest/features/structured_outputs.html) and [XGrammar EBNF](https://xgrammar.mlc.ai/docs/defining_structures/ebnf_grammar.html) — what grammar-constrained decoding can and cannot enforce. [PICARD, arXiv 2109.05093](https://arxiv.org/abs/2109.05093) and [execution-guided decoding, arXiv 1807.03100](https://arxiv.org/abs/1807.03100) — why to prefer execute-then-select.

**Semantic layers.** [dbt Labs semantic layer vs text-to-SQL, 2026](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026) — 90.0→98.2 and 84.1→100.0, the deterministic-SQL mechanism, and the fails-loudly-vs-silently argument. [dbt MetricFlow](https://docs.getdbt.com/docs/build/about-metricflow) — metric types, deliberate omission of arbitrary join logic, missing MSSQL/Oracle/MySQL support. [lkr.dev benchmark](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/) — Looker NL2LookML 97% vs BigQuery NL2SQL 80%, and 30%→80% from authored context. [Snowflake Cortex Analyst](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/) — 90%+ vs GPT-4o's 51% on the same 150 questions, single-pre-joined-view scope, multiple-acceptable-gold scoring. [Cube for AI agents](https://cube.dev/articles/semantic-layer-for-ai-agents-2026) — compile-time governance, "a SELECT is not access control," and why post-hoc SQL linting is brittle. [Malloy](https://docs.malloydata.dev/documentation/) — an implementation option with no correctness claim.

**Catalog and dialect metadata.** [Snowflake INFORMATION_SCHEMA](https://docs.snowflake.com/en/sql-reference/info-schema) — role-dependent output, no DDL consistency guarantee, selectivity error, running-warehouse requirement, semantic views, history retention windows. [Oracle ALL_TAB_COLUMNS](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html) — no INFORMATION_SCHEMA, prefix conventions, free optimizer statistics. [Microsoft Learn INFORMATION_SCHEMA views](https://learn.microsoft.com/en-us/sql/relational-databases/system-information-schema-views/system-information-schema-views-transact-sql?view=sql-server-ver17) — ISO compliance and the backward-compatibility break.

**Safety and governance.** [PostgreSQL client config](https://www.postgresql.org/docs/current/runtime-config-client.html) — `default_transaction_read_only`, `statement_timeout` (zero disables), `lock_timeout`, `idle_in_transaction_session_timeout`. [PostgreSQL RLS](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) — default-deny, `BYPASSRLS`, owner bypass and `FORCE ROW LEVEL SECURITY`, leakproof side-channel. [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) — indirect injection definition and the quoted mitigations.

**Production evaluation and ambiguity.** [STEF, arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1) — gold-free scoring, the Φ formula and 90/75/50 thresholds, λ_min = 1000, and stated degradation on nested/window queries. [Google Cloud text-to-SQL techniques](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql) — deterministic parsing and dry runs as complements, implicit context, ambiguity clarification, synthetic multi-dialect benchmarks. [AmbiSQL, arXiv 2508.15276v2](https://arxiv.org/html/2508.15276v2), [AMBROSIA](https://www.research.ed.ac.uk/en/publications/ambrosia-a-benchmark-for-parsing-ambiguous-questions-into-databas/), [AmbiQT](https://ar5iv.labs.arxiv.org/html/2310.13659), [PRACTIQ](https://arxiv.org/html/2410.11076v1), and [CLUES](https://ar5iv.labs.arxiv.org/html/2602.12015) — the ambiguity-detection inventory; CLUES gives the 51%-of-errors-in-25%-of-queries gating result.
