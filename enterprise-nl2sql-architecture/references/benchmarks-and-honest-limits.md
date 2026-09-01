# Benchmarks and Honest Limits

Read this before quoting any accuracy number to a stakeholder, writing a customer-facing SLA,
or accepting a roadmap premise like "the model will handle it." Every number here carries its
source URL. Values that could not be confirmed from a primary source are marked **n.a.** and
must not be asserted.

## The one-paragraph version

Published evidence puts an unconstrained "LLM + schema → SQL" system on real enterprise
warehouses in the **3-12% execution-accuracy** band, not the 80-90% band Spider leaderboards
advertise. The three interventions with large, independently reproduced effect sizes are
(a) narrowing what the model may reference (retrieval-based schema linking, semantic layers),
(b) refusing to trust the model's identifiers (compile-time validation against a harvested
catalog), and (c) generating multiple candidates and selecting with execution feedback.
Everything else is second-order, including prompt engineering.

## Spider 1.0 — the number vendors quote

[Spider 1.0](https://yale-lily.github.io/spider) is 10,181 questions and 5,693 unique complex
SQL queries over 200 databases in 138 domains ([Yale LILY Spider](https://yale-lily.github.io/spider)).

| System | Spider test EX | Date |
|---|---|---|
| MiniSeek | 91.2 | Nov 2, 2023 ([Spider leaderboard](https://yale-lily.github.io/spider)) |
| DAIL-SQL + GPT-4 + Self-Consistency | 86.6 | Aug 20, 2023 ([Spider leaderboard](https://yale-lily.github.io/spider)) |
| DAIL-SQL + GPT-4 | 86.2 | Aug 9, 2023 ([Spider leaderboard](https://yale-lily.github.io/spider)) |
| DPG-SQL + GPT-4 + Self-Correction | 85.6 | ([Spider leaderboard](https://yale-lily.github.io/spider)) |
| DIN-SQL + GPT-4 | 85.3 | Apr 21, 2023 ([Spider leaderboard](https://yale-lily.github.io/spider)) |
| C3 + ChatGPT (zero-shot) | 82.3 | ([Spider leaderboard](https://yale-lily.github.io/spider)) |
| RESDSQL-3B + NatSQL | 79.9 | ([Spider leaderboard](https://yale-lily.github.io/spider)) |

Exact-set-match on the same page: MiniSeek 81.5 test / 80.3 dev; Graphix-3B+PICARD 74.0 test
([Spider leaderboard](https://yale-lily.github.io/spider)).

**Why it is misleading here:** Spider databases average **5.1 tables and 25.7 columns per
database** ([BEAVER paper, arXiv 2409.02038v3](https://arxiv.org/html/2409.02038v3)). That is
not a warehouse; that is a toy. Self-consistency, notably, moved DAIL-SQL+GPT-4 only
**86.2 → 86.6**, a +0.4 point gain ([Spider leaderboard](https://yale-lily.github.io/spider)) —
so do not budget for string-level voting as an accuracy lever.

## Spider 2.0 — the enterprise reality check

[Spider 2.0](https://spider2-sql.github.io/) (ICLR 2025 Oral) is **632 real-world enterprise
workflow problems**, databases that often exceed 1,000 columns, and SQL workflows that often
exceed 100 lines ([Spider 2.0 site](https://spider2-sql.github.io/)). Settings: Spider 2.0-Snow
(547 Snowflake examples), Spider 2.0-DBT (68 DuckDB code-agent examples, created 2025-05-22),
Spider 2.0-Lite (547: BigQuery 214, Snowflake 198, SQLite 135)
([Spider 2.0 site](https://spider2-sql.github.io/)).

The headline gap from the paper: an o1-preview code-agent framework solves only **21.3%** of
Spider 2.0 tasks versus **91.2%** on Spider 1.0 and **73.0%** on BIRD
([arXiv 2411.07763](https://arxiv.org/abs/2411.07763)). The project site reports **o1-preview
17.1%** and **GPT-4o 10.1%**, against GPT-4o's **86.6%** on Spider 1.0
([Spider 2.0 site](https://spider2-sql.github.io/)).

Spider 2.0-Snow leaderboard (fetched Aug 2026, [Spider 2.0 site](https://spider2-sql.github.io/)):

| Rank | Method | EX % |
|---|---|---|
| 1 | Genloop Sentinel Agent v2 Pro | 96.70 |
| 2 | Native mini (usenative.ai) | 96.53 |
| 3 | QUVI-3 + Gemini-3-pro-preview (DAQUV) | 94.15 |
| 4 | TCDataAgent-SQL (Tencent Cloud) | 93.97 |
| 5 | Prism Swarm + Deepthink + Claude-Sonnet-4.5 (Paytm) | 90.49 |
| 8 | AT&T CDO & RelationalAI "Ask Data" w/ Relational Knowledge Graph | 86.28 |
| 17 | Arctic-FLEX (Snowflake AI Research) | 75.14 |
| 27 | ReFoRCE + o3 | 62.89 |
| 40 | ReFoRCE + o1-preview | 31.26 |
| 42 | Spider-Agent + Claude-4-Sonnet | 25.78 |
| 58 | DAIL-SQL + GPT-4o | 2.20 |
| 59 | CHESS + GPT-4o | 1.28 |
| 60 | DIN-SQL + GPT-4o | 0.00 |
| 61 | SFT CodeS-15B | 0.00 |

### Treat the above-90% entries with suspicion

Four caveats come from the site itself
([Spider 2.0 site](https://spider2-sql.github.io/)):

1. Spider 2.0-Snow "includes well-prepared database metadata and documentation" — curated
   metadata, which is exactly the variable that is absent in a client's raw warehouse.
2. Methods marked `-*` use **ground-truth tables** and are excluded from ranking; oracle tables
   were provided on 2025-04-20.
3. "Scores may change slightly over time" — the leaderboard exhibits score drift.
4. **Gold answers were released 2024-12-24**, and on 2025-01-07 the maintainers had to publish a
   warning not to SFT on gold SQL.

So the 96.7% number does not measure "can an agent find the right tables in a 10,000-table
warehouse." The honest signal on that page is the bottom: **DIN-SQL 0.00%, CHESS 1.28%,
DAIL-SQL 2.20%** — pipelines that scored 85-86% on Spider 1.0.

## BIRD and BIRD-CRITIC

[BIRD](https://bird-bench.github.io/) is 12,751 unique question-SQL pairs over 95 big databases
totaling 33.4 GB across 37+ professional domains ([BIRD site](https://bird-bench.github.io/)).
**Human performance on test is 92.96% EX with R-VES 83.26**
([BIRD site](https://bird-bench.github.io/)) — the human-vs-machine gap is the number to quote.

Top BIRD test EX ([BIRD leaderboard](https://bird-bench.github.io/)):

| Method | Test EX | Dev EX | Date |
|---|---|---|---|
| AskData + GPT-4o (AT&T CDO-DSAIR) | 81.95 | 77.64 | Dec 16, 2025 |
| Agentar-Scale-SQL (Ant Group) | 81.67 | 74.90 | Sep 25, 2025 |
| Sber Text2SQL | 81.33 | n.a. | Jun 19, 2026 |
| Xiaomi Text2SQL | 80.83 | n.a. | May 27, 2026 |
| RAS (Adya AI) | 79.82 | n.a. | Aug 19, 2026 |
| DeepEye (HKUST-GZ) | 79.09 | n.a. | Jul 14, 2026 |
| MarkovSQL | 78.70 | n.a. | n.a. |
| DeepEye-SQL 27B | 78.42 | n.a. | n.a. |
| Spektr-SQL (Amazon Ads) | 78.31 | n.a. | n.a. |
| DataGallery-Text2SQL (Huawei) | 77.53 | n.a. | n.a. |

Top R-VES (efficiency-weighted): Agentar-Scale-SQL 77.00; AskData+GPT-4o 76.31; XiYan-SQL 71.41
(Dec 17, 2024); ExSL+granite-34b-code (IBM) 71.37
([BIRD leaderboard](https://bird-bench.github.io/)). BIRD databases average **6.8 tables and
72.5 columns** ([BEAVER paper](https://arxiv.org/html/2409.02038v3)) — still an order of
magnitude below the target scenario.

**BIRD-CRITIC / SWE-SQL** measures the *debugging* skill the system actually needs, because
generated SQL fails constantly. 530 PostgreSQL tasks (BIRD-CRITIC-PG) plus 570 multi-dialect
tasks (PostgreSQL, MySQL, SQL Server, Oracle). **O3-Mini scores 38.87% on Postgres and 33.33%
on multi-dialect**; Bird-Fixer (Qwen-2.5-Coder-14B fine-tune) reaches 38.11% PG / 29.65% Multi,
surpassing Claude-3.7-Sonnet and GPT-4.1
([arXiv 2506.18951v1](https://arxiv.org/html/2506.18951v1)). The open split
`bird-critic-1.0-open` is 600 dev tasks plus 200 held-out OOD, dialect-split PG 300 / MySQL 100 /
SQL Server 100 / Oracle 100 ([BIRD-CRITIC repo](https://github.com/bird-bench/BIRD-CRITIC-1)).
On Mar 23, 2026 a SQLite variant (500 issues) plus BIRD-Talon-14B/7B and BIRD-Zeno-7B were
released ([BIRD-CRITIC repo](https://github.com/bird-bench/BIRD-CRITIC-1)).

**Design consequence:** cap the repair loop. A repair loop whose oracle fixes ~33-39% of real
issues is worth two retries, not ten.

## BEAVER — the number to plan around

[BEAVER](https://arxiv.org/html/2409.02038v3) is built from **three private enterprise data
warehouses**: 9,128 question-SQL pairs (254 harvested from real query logs and reports, 8,874
expert-verified synthetic), 8 databases, **812 tables, 6,955 columns**, 19 domains
([BEAVER paper](https://arxiv.org/html/2409.02038v3)).

| Benchmark | Tables / DB | Columns / DB |
|---|---|---|
| WikiSQL | 1.0 | 6.3 |
| Spider | 5.1 | 25.7 |
| BIRD | 6.8 | 72.5 |
| Spider 2.0 | 52.6 | 803.6 |
| **BEAVER** | **101.5** | **869.4** |

Average per-database join degree 9.8. Average gold query: 316.7 tokens, 4.0 tables, 5.7 joins,
8.0 functions, 5.6 nesting levels, 3.7 CTEs
([BEAVER paper](https://arxiv.org/html/2409.02038v3)).

End-to-end EX on BEAVER ([BEAVER paper](https://arxiv.org/html/2409.02038v3)):

| System | EX % |
|---|---|
| ReFoRCE + Claude-4.5-sonnet | 11.4 |
| ReFoRCE + GPT-5.2 | 10.8 |
| ReFoRCE (overall) | 9.5 |
| Few-shot prompting | 7.6 |
| DIN-SQL | 5.1 |
| DAIL-SQL | 3.6 |

The same ReFoRCE agent scores **62.9% on Spider 2.0 and 11.4% on BEAVER**. Real logged queries
are far easier than synthetic ones (ReFoRCE **32.0%** real subset vs **7.2%** synthetic), and
**oracle subtask annotations** lift it to **25.9%** (Setting 2), with the abstract quoting
**30.1%** ([BEAVER paper](https://arxiv.org/html/2409.02038v3)).

Error taxonomy over 275 sampled wrong queries
([BEAVER paper](https://arxiv.org/html/2409.02038v3)): analytical/structural 46.8%;
**schema-linking 35.2%**; grouping/ordering 22.8%; predicate errors 18.0%; advanced functions
14.2%; column selection 12.5%; table selection 11.8%; join-related 10.9%; omitted required
predicates 10.6%. Inter-annotator agreement ~83% (question-SQL), ~87% (subtasks).

Two things follow. Schema linking at 35.2% is the largest single addressable bucket, which is
why retrieval is the top-priority investment. And analytical/structural at 46.8% is *not*
addressable by better identifier grounding — it is addressable only by decomposition, semantic
layers, and refusal.

## The gradient is the enterprise reality tax, not noise

The three benchmarks differ mainly in **schema size, metadata quality, and query length** — not
in required SQL language features. Accuracy for the *same* systems falls roughly
**86% → 10-21% → 4-11%** along Spider → Spider 2.0 → BEAVER. Do not model this as benchmark
noise or as something a next-generation model erases.

1. **Schema scale is the dominant independent variable.** Anything that shrinks the candidate
   schema before generation buys more than any prompt technique.
2. **Metadata quality is second.** Spider 2.0-Snow's high scores come with "well-prepared
   database metadata and documentation" ([Spider 2.0 site](https://spider2-sql.github.io/));
   BEAVER's low scores come from real warehouses without that curation. Product accuracy is a
   function of the catalog you build, not the model you buy.
3. **Plan for repair, not one-shot correctness** — but bound it, per BIRD-CRITIC
   ([arXiv 2506.18951v1](https://arxiv.org/html/2506.18951v1)).

## Accuracy bands to quote a customer

| Configuration | Band | Evidence |
|---|---|---|
| Raw schema, large warehouse | **10-30%** | ([Spider 2.0](https://spider2-sql.github.io/), [BEAVER](https://arxiv.org/html/2409.02038v3)) |
| Retrieval + validation + candidate selection on a curated catalog | **no published number for this exact configuration (n.a.)**; LinkedIn production reports 48-53% "good or better" on its own 133-question benchmark | ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)) |
| Governed semantic layer, in-scope questions | **90-100%** | ([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026), [Snowflake](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)) |

Never quote a Spider number for this product. If pressed for a single figure, quote BEAVER's
11.4% best-in-class alongside the mitigation deltas in
`references/retrieval-and-catalog.md` — that is the defensible framing.

## Semantic-layer evidence (the 90-100% band)

**dbt Labs, April 7, 2026** — ACME Insurance benchmark (originally Juan Sequeda et al. at
data.world), **11 questions × 20 runs**, four configurations, models Opus 4.6 / Sonnet 4.6 /
GPT-5.3 Codex / GPT-5.2 across reasoning efforts
([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)):

| Model | Method | Accuracy |
|---|---|---|
| claude-sonnet-4-6 | Text-to-SQL | 90.0% |
| claude-sonnet-4-6 | Semantic Layer | 98.2% |
| gpt-5.3-codex | Text-to-SQL | 84.1% |
| gpt-5.3-codex | Semantic Layer | 100.0% |

Semantic-layer advantage spans **24.7-50.0 pp across all 18 per-effort rows**; e.g. gpt-5.3-codex
at effort `none` is 100.0 SL vs 50.0 text-to-SQL
([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)). Mechanism: the
LLM only decomposes the question into metrics + dimensions, and **MetricFlow generates the SQL
deterministically**, so the LLM "cannot produce an incorrect join" or "a bad aggregation." The
stated trade-off is coverage — only modeled questions are answerable
([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)).

Skeptical caveats to state alongside it: n = 11 questions; the vendor sells semantic layers; to
make the text-to-SQL arm work at all "the entire schema was loaded as context," which the blog
concedes is impractical at scale; and the widely repeated "32.7% → 64.5%" 2023 baseline is
**n.a.** from the primary page
([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)).

**Independent replication, larger n.** lkr.dev, same ACME dataset, **44 questions × 3 runs (132
executions)** via the Gemini Data Analytics / Conversational Analytics API, Looker backend
(NL2LookML) vs BigQuery backend (NL2SQL)
([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)):

| Backend | Avg answer correctness | Avg run success rate |
|---|---|---|
| BigQuery / NL2SQL | 80% | 100% |
| Looker / NL2LookML | 97% | 99% |

Per-run: BigQuery 35/44 (80%), 33/44 (75%), 37/44 (84%); Looker 43/44 (97%), 41/44 (93%), 44/44
(100%). **BigQuery NL2SQL started at 30% before authored context was added**, rising to 80% only
after table-relationship and column metadata plus custom system instructions. **7 questions
failed all three BigQuery runs** (loss-ratio calculations, multi-hop joins linking Agents and
Policy Holders to claims, unaggregated premium listings); **0 failed all three Looker runs**.
Looker handled fan-out via **symmetric aggregates**. Stated limitations: all questions are
descriptive analytics, no custom window functions or conditional groupings, which the author says
are "often better suited for NL2SQL"
([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)).

**The original academic result (2023).** GPT-4 zero-shot directly on an enterprise insurance SQL
schema: **16%**. Over a knowledge-graph (ontology + mappings) representation of the same
database: **54%** ([arXiv 2311.07509](https://arxiv.org/abs/2311.07509)). The cleanest published
statement that *context representation*, not model capability, was the binding constraint.

**Snowflake Cortex Analyst** claims **90%+ SQL accuracy**, "nearly 2×" GPT-4o single-prompt, and
"about 14% more accurate" than another market solution, on an internal **150-question** benchmark
spanning sales/marketing/finance at three difficulty levels. **GPT-4o scored 51% on the same
set** ([Snowflake, Aug 29, 2024](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)).
Two honesty notes from that page: initial scope is **a single view with pre-joined data**, with
cross-table star/snowflake joins explicit future work; and Snowflake rejects plain execution
accuracy for a **multiple-acceptable-gold-query** protocol with human-curated answers and column
precision/recall at a lenient threshold.

### Semantic-layer tool constraints that bite this scenario

| Tool | Platform support | Note |
|---|---|---|
| dbt MetricFlow | Snowflake, BigQuery, Databricks, Postgres (dbt Core only), Redshift | **No MSSQL, no Oracle, no MySQL.** Apache 2.0; requires dbt ≥ 1.6; latest metric spec dbt v1.12+ ([dbt MetricFlow docs](https://docs.getdbt.com/docs/build/about-metricflow)) |
| Cube | broad; Apache 2.0 core | No quantitative accuracy numbers published on the fetched page — cite it for the governance argument, not for accuracy ([Cube](https://cube.dev/articles/semantic-layer-for-ai-agents-2026)) |
| Malloy | BigQuery, Postgres, Parquet/CSV via DuckDB | Makes **no explicit correctness-superiority claim** — cite as an implementation option only ([Malloy docs](https://docs.malloydata.dev/documentation/)) |
| LookML / Looker | n/a | Quantitative case is the lkr.dev benchmark; official Looker docs not fetched: **n.a.** |

MetricFlow "handles SQL query construction," lets the engine "determine the best path between
tables," captures identifier types but **deliberately does not capture arbitrary join logic**,
explicitly to avoid fan-out and chasm joins. Metric types: simple, ratio, derived, cumulative,
conversion ([dbt MetricFlow docs](https://docs.getdbt.com/docs/build/about-metricflow)).

**Where the "just use a semantic layer" argument fails for this product:** you do not control the
client's data model. A semantic layer is a precondition you cannot impose on a customer who hands
you 400 Oracle databases and expects answers on day one — and MetricFlow does not support Oracle
or MSSQL at all. Defensible synthesis: a thin, auto-bootstrapped, per-tenant semantic layer over
the highest-traffic metrics, full text-to-SQL as the fallback path, route on whether the question
maps to a modeled metric, and report confidence differently for the two paths.

## Pipeline scoreboard — adopt mechanisms, not pipelines

| Pipeline | Mechanism | Published score | Spider 2.0-Snow |
|---|---|---|---|
| DIN-SQL | Decomposed in-context learning | Spider 85.3 ([leaderboard](https://yale-lily.github.io/spider)) | **0.00%** ([Spider 2.0](https://spider2-sql.github.io/)) |
| DAIL-SQL | Prompt-engineering study | Spider 86.6 ([arXiv 2308.15363](https://arxiv.org/abs/2308.15363)) | **2.20%** ([Spider 2.0](https://spider2-sql.github.io/)) |
| CHESS | 4 agents: IR, Schema Selector, Candidate Generator, Unit Tester | BIRD test 66.69-71.10 ([ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755), [arXiv](https://arxiv.org/abs/2405.16755)); Spider test 87.2 ([ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)) | **1.28%** ([Spider 2.0](https://spider2-sql.github.io/)) |
| CHASE-SQL | 3 candidate generators + pairwise selection agent | BIRD test **73.0%**, dev 73.01% ([arXiv 2410.01943](https://arxiv.org/abs/2410.01943)) | n.a. |
| MCS-SQL | Multiple prompts + multiple-choice selection | BIRD **65.5%**, Spider **89.6%** ([arXiv 2405.07467](https://arxiv.org/abs/2405.07467)) | n.a. |
| XiYan-SQL | M-Schema + multi-generator ensemble + refiner + fine-tuned selector | BIRD 75.63%, Spider test 89.65%, SQL-Eval 69.86%, NL2GQL 41.20% ([arXiv 2411.08599](https://arxiv.org/abs/2411.08599)) | n.a. (BIRD R-VES 71.41, [BIRD leaderboard](https://bird-bench.github.io/)) |
| ReFoRCE | Agent | Spider 2.0-Snow 62.89% (+o3) / 31.26% (+o1-preview) ([Spider 2.0](https://spider2-sql.github.io/)) | BEAVER 9.5-11.4% ([BEAVER](https://arxiv.org/html/2409.02038v3)) |

Note CHESS's internal inconsistency: the body reports BIRD test 66.69% while the abstract reports
**71.10%** at a higher compute budget — cite the version you rely on
([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755),
[arXiv 2405.16755](https://arxiv.org/abs/2405.16755)).

**Reranking is the highest-leverage mechanism in this table.** CHASE-SQL generates candidates
three ways — divide-and-conquer decomposition in a single LLM call, chain-of-thought based on
query **execution plans**, and instance-aware synthetic example generation — then ranks with a
**fine-tuned binary candidate-selection LLM using pairwise comparisons**, which the authors state
is "more robust over alternatives" ([arXiv 2410.01943](https://arxiv.org/abs/2410.01943)).
MCS-SQL confirms the pattern independently: multiple prompts for schema linking, diverse
candidates on the refined schema, confidence filtering, multiple-choice selection
([arXiv 2405.07467](https://arxiv.org/abs/2405.07467)).

**Execution-guided decoding** in its original form (excluding faulty programs during decoding by
conditioning on partial-program execution, then-SOTA **83.8% on WikiSQL**,
[arXiv 1807.03100](https://arxiv.org/abs/1807.03100)) must **not** be ported naively — executing
partial queries against a live client warehouse per decoding step is a cost, latency, and safety
non-starter. The modern equivalent is execute-then-select over complete candidates.

## Serialization format: unresolved, do not overclaim

**M-Schema** is a semi-structured schema representation from XiYan-SQL "designed to improve DB
structure understanding" ([arXiv 2411.08599](https://arxiv.org/abs/2411.08599)). The reference
implementation is a `SchemaEngine` over SQLAlchemy emitting `mschema.to_mschema()`, with
PostgreSQL/MySQL/SQLite shown and the README claiming "MySQL, PostgreSQL, Oracle, etc."
([M-Schema repo](https://github.com/XGenerationLab/M-Schema)). **The repo does not publish the
serialized format itself, nor any head-to-head accuracy comparison against DDL or MAC-SQL
formats — both n.a.** Do not repeat "M-Schema beats DDL by X points."

LinkedIn uses plain `CREATE TABLE` representation for its column ranker
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). DAIL-SQL is the citable systematic
comparison of question representations, example selection, and example organization, landing at
**86.6% EX on Spider** with explicit token-efficiency emphasis
([arXiv 2308.15363](https://arxiv.org/abs/2308.15363)). Default to `CREATE TABLE`; treat
M-Schema as an unverified candidate to A/B, not a decision.

## Counter-evidence you must weigh

"The Death of Schema Linking?" argues newer LLMs use relevant schema elements even amid many
irrelevant ones, forgoes schema linking whenever the schema fits the context window, substitutes
augmentation/selection/correction, and ranked **first on BIRD at 71.83%**
([arXiv 2408.07702](https://arxiv.org/abs/2408.07702)). The result is real but scope-limited:
BIRD databases average 6.8 tables ([BEAVER paper](https://arxiv.org/html/2409.02038v3)), and
"fits in the context window" is precisely the condition that fails at 10,000 tables. Do not
generalize it.

## Explicit gaps — do not assert these

- M-Schema serialized format and any accuracy comparison vs DDL / MAC-SQL: **n.a.**
- ADBC driver maturity per engine; Trino connector list; Calcite named dialect list; Substrait
  implementation maturity: **n.a.**
- Postgres / MySQL / BigQuery INFORMATION_SCHEMA reference pages; Oracle constraint views; RLS
  equivalents for MSSQL / MySQL / Oracle VPD / Snowflake / BigQuery: **n.a.**
- LookML official documentation; Cube quantitative accuracy: **n.a.**
- PICARD exact Spider/CoSQL numbers from the abstract page: **n.a.**
- STEF human-agreement correlation coefficients: **n.a.**
  ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1))
- SOC 2 / HIPAA control mappings for NL2SQL audit: **n.a.**
- Uber QueryGPT, EntSQL (arXiv 2606.03363), SQL-GEN dialect gap (arXiv 2408.12733), cost-aware
  text-to-SQL (arXiv 2512.22364), NL2SQL survey (arXiv 2408.05109), IBM Text-to-SQL Evaluation
  Toolkit: found via search, pages not fetched — verify before citing.
