# Retrieval, Grounding, and the Offline Catalog

Read this when building or debugging the retrieval funnel, the metadata harvesters, the value
index, or the catalog refresh jobs. This is where the accuracy actually comes from.

## Trap first: the four ways this silently fails

1. **You put schemas into the table ranker.** LinkedIn measured that including schemas in the
   table ranker *lowered recall and increased latency*
   ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). The intuitive move is the wrong
   move.
2. **You drop PK/FK columns because they scored low.** PKs are needed for counting and FKs for
   joins, and they "often look semantically unrelated to the question" — CHESS always retains
   linking columns regardless of filter output
   ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).
3. **You compute value similarity on the fly.** Naive edit distance over all unique values takes
   **≈ 5 minutes**; the LSH-indexed path takes **≈ 5 seconds**
   ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).
4. **You harvest the catalog with a different role than you query with.** Snowflake's
   INFORMATION_SCHEMA returns "only objects for which the current role has been granted access
   privileges" ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)), so a
   privileged harvest produces a catalog that promises tables the query role cannot read — which
   presents as a permission error at execution time, after the user got an answer preview.

## Why you cannot put 10k tables in a prompt

Two independent, documented reasons.

**Cost/latency.** CHESS's Schema Selector improves accuracy ~2% while reducing LLM tokens **×5**,
and reaches 71.10% on BIRD test with ~**83% fewer LLM calls** than the leading proprietary method
it matches within 2% ([arXiv 2405.16755](https://arxiv.org/abs/2405.16755)).

**Accuracy.** CHESS reports that supplying *all* column descriptions "can overwhelm the model and
lead to incorrect SQL queries," and that selective retrieval outperforms naive context
augmentation by **4.76% EX**
([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)). dbt is blunter: to make
text-to-SQL work at all they "loaded the entire schema as context," which is "stated to be
impractical for larger datasets"
([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)).

## The LinkedIn SQL Bot funnel — the reference architecture

The single most useful published enterprise system description. Live since **July 2024**,
generates **Trino SQL**, operates over a data lake with **millions of tables** where popular
tables exceed 100 columns ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

| Stage | Parameter | Detail |
|---|---|---|
| 1. User-dataset clustering | `N_comp = 200` ICA components, `T_c = 20` tables per cluster | Three months of query history; clustering job completes in **15 minutes at p90** |
| 2. Table retrieval | `K_ret = 20` | Hybrid over names, human descriptions, AI descriptions, usage popularity |
| 3. Table ranker | `K_rnk = 7`, scores 1-10 | **Deliberately omits schemas** — including them lowered recall and raised latency |
| 4. Column ranker | two tiers: relevant / potentially relevant | Uses a plain `CREATE TABLE` representation, following Gao et al. 2023 |

All values from ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

**The ablation is the evidence** ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)):

| Configuration | Table recall | Column recall | Score(4+) | Compilation success | Valid tables/columns |
|---|---|---|---|---|---|
| Full config | 78% | 56% | 48% | 96% | 99% |
| A.1: schemas only (no knowledge graph) | 45% | 24% | **9%** | 88% | n.a. |
| B.1: no rankers / no fixer | n.a. | n.a. | n.a. | 66% | 77% |

End-to-end effects claimed: score **9% → 49%**; **schema hallucination 23% → 1%**; compilation
errors **34% → 4%** ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Expert review of
124/133 questions: **53% rated 4-5, 77% rated 3+**; most common remaining issue is an incorrect
filter (24%), with incorrect joins only 4%. Adoption: **>300 weekly active users**, 33% of
sessions lead to pasted code, ~20% week-over-week return rate, 39% rate queries very
good/excellent, 95% at least "passes"
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

**Negative results — internalize these before you build them.** An extra "approach generation"
LLM call did not improve recall. A query-planner LLM added latency, over-nested the queries, and
*lowered* recall and quality ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Do not
add planner or approach-generation stages on intuition; both were measured and rejected.

Calibration figures from the same paper: Spider went 54% (May 2020) → >90% (Nov 2023), BIRD 40%
(Mar 2023) → 76% (Apr 2025), Spider 2.0 best 31% (Apr 2025), and an internal Uber application
achieved 50% table overlap ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

## The four-level retrieval architecture

Design guidance, not from a single doc; each level cuts the space by roughly an order of
magnitude.

1. **Tenant → database/domain routing.** Route on business-domain classification plus historical
   usage, not embeddings alone. LinkedIn's ICA clustering over 3 months of query logs is the
   published instantiation ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Uber's
   QueryGPT uses an intent agent mapping the question to business domains/workspaces backed by a
   vector DB and similarity search ([Uber engineering blog](https://www.uber.com/us/en/blog/query-gpt/) —
   lead found via search; page not fetched, treat details as unverified).
2. **Table retrieval** — hybrid BM25/keyword + embedding over table names, human descriptions,
   AI-generated descriptions, and usage popularity. Return ~20
   ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
3. **Table reranking without schemas** to ~7
   ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
4. **Column filtering with PK/FK force-include**
   ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).

Run the **LSH/embedding value index for literal grounding as a separate index**, refreshed
independently of the structural catalog
([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).

## CHESS three-stage schema selection and its measured funnel

Stages ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)):

- **Individual column filtering** — binary relevance classification per column, given table name,
  column name, data type, retrieved description, retrieved values, plus few-shot examples.
  Columns are evaluated **in isolation**.
- **Table selection** — global reasoning over the filtered schema. Removing it costs **6.12%**.
- **Final column selection** — chain-of-thought justification, then a minimal column set.
- **Linking columns (PK/FK) always retained** regardless of filter output.

Worked funnel on a Formula 1 database
([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)):

| Stage | Tables | Columns |
|---|---|---|
| Initial schema | 13 | 96 |
| After individual column filtering | 13 | 36 |
| After table selection | 2 | 7 |
| After final column selection | 2 | 5 |

CHESS's error analysis on a 147-question subsample: vanilla GPT-4's wrong SQL is **57.1%
schema-linking issues**, with wrong columns in SELECT/JOIN at 26.0%; CHESS reduces incorrect
column linking to **5.4%** ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).

## Literal grounding — the LSH value index

This is the mechanism that stops `WHERE region = 'North America'` when the column stores `'NA'`.

Pipeline ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)):

1. Few-shot prompt extracts keywords, keyphrases, and named entities from the question.
2. Each keyword is **split on spaces into individual words**, making the search order-invariant,
   because entities in questions rarely match stored formatting.
3. **Unique database values are indexed with LSH during preprocessing.** At query time the LSH
   index returns the **top 10** similar values.
4. Candidates are refined with **edit distance** (syntactic) and **cosine similarity over
   embeddings** (semantic), using OpenAI `text-embedding-3-small` in their implementation; values
   below a similarity threshold are dropped (threshold value: **n.a.** — determine empirically and
   pin it in a test).
5. For each (keyword, column) pair only the value with the **smallest edit distance** is retained;
   a target retrieval set of ~100 elements is given as acceptable.
6. Measured: naive on-the-fly edit distance over all unique values **≈ 5 minutes**; LSH-indexed
   **≈ 5 seconds**.

Catalog descriptions are separately embedded into a vector store (ChromaDB in their
implementation) and retrieved by semantic similarity to the question and keywords, returning only
"minimally sufficient" descriptions
([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).

For high-cardinality columns, "including all distinct values as sample values is described as
unrealistic," and Snowflake's answer is semantic search over the column's values via **Cortex
Search** ([Snowflake](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)) —
the same problem, the same shape of solution. Build the equivalent.

**Security note:** this step injects customer-controlled cell values into your prompt by design.
See `references/safety-and-governance.md` — this is the primary indirect prompt-injection surface.

## What to store beyond DDL

LinkedIn's node attribute set is the best published template:
**Human Description, AI Description, Usage Popularity, Table Cluster, Certification/Deprecation
Status, Top Values, Is Partition Key**
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Their sources: DataHub metadata,
query logs, wikis, code repositories, jargon glossaries, and crowdsourced domain knowledge
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

Google frames the same need as **implicit context**: LLMs need "the database schema, relevant
columns, and what the data looks like, as well as implicit context, such as the precise semantic
meaning of data," with the concrete example that an accurate shoe-sales query requires knowing
`cat_id2 = 'Footwear'` in a `pcat_extension` table means the product is a shoe. Google explicitly
rejects per-database fine-tuning as "typically not scalable" because of schema/data churn and
cost, and notes business semantics "are often poorly documented and difficult to turn into
training data" ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).

**Do not fine-tune per client database.** That is the documented anti-pattern, and it is also
where a naive roadmap will spend its entire GPU budget.

## Per-dialect harvesters — INFORMATION_SCHEMA is not a portable API

Write **one harvester per dialect** behind a single normalized catalog schema. Do not attempt a
single portable SQL query.

| Engine | Catalog surface | Confirmed caveats |
|---|---|---|
| PostgreSQL | `information_schema` + `pg_catalog` | Specific reference page not fetched: **n.a.** |
| MySQL | `information_schema` | Not fetched: **n.a.** |
| SQL Server | `INFORMATION_SCHEMA` views | The views "comply with the ISO standard definition," provide "an internal, system table-independent view of the SQL Server metadata," and "**Some changes were made to the information schema views that break backward compatibility**" ([Microsoft Learn](https://learn.microsoft.com/en-us/sql/relational-databases/system-information-schema-views/system-information-schema-views-transact-sql?view=sql-server-ver17)). The fetched page does **not** recommend `sys.*` instead — a commonly repeated claim, unconfirmed here (**n.a.**) |
| Oracle | **No INFORMATION_SCHEMA.** Data dictionary: `ALL_TAB_COLUMNS` "describes the columns of the tables, views, and clusters accessible to the current user," with `OWNER`, `TABLE_NAME`, `COLUMN_NAME`, `DATA_TYPE`, `NUM_DISTINCT`, `NUM_NULLS`, `LOW_VALUE`, `HIGH_VALUE`, `DENSITY` ([Oracle docs](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html)) | Prefixes: `ALL_*` = accessible to current user, `DBA_*` = all objects, `USER_*` = owned by current user (and `USER_TAB_COLUMNS` **omits `OWNER`**). `ALL_TAB_COLUMNS` **filters out system-generated hidden columns**; `ALL_TAB_COLS` does not ([Oracle docs](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html)) |
| Snowflake | `INFORMATION_SCHEMA` per database, "based on the SQL-92 ANSI Information Schema, but with the addition of views and functions that are specific to Snowflake," read-only, auto-created in every database ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)) | Four hard caveats: (1) "**Queries on INFORMATION_SCHEMA views do not guarantee consistency with respect to concurrent DDL**"; (2) output depends on the current role's privileges; (3) insufficiently selective filters **error out** rather than run; (4) "The Snowflake-specific views are subject to change" — avoid `SELECT *`. Unquoted identifiers are stored uppercase, so query them uppercase, and the views require a **running warehouse** |
| BigQuery | `INFORMATION_SCHEMA` | Specific page not fetched: **n.a.** Dry run is documented for validation and cost ([BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)) |

Snowflake's exact catalog-guard error string to handle in the harvester:
`Information schema query returned too much data. Please repeat query with more selective
predicates.` ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)) — page
by schema and object-name prefix.

Snowflake's INFORMATION_SCHEMA now also exposes `SEMANTIC_VIEW`, `SEMANTIC_METRICS`,
`SEMANTIC_DIMENSIONS`, `SEMANTIC_FACTS`, and `SEMANTIC_RELATIONSHIPS` views
([Snowflake info schema docs](https://docs.snowflake.com/en/sql-reference/info-schema)) — i.e.
the client's semantic layer is becoming first-class catalog metadata you can harvest for free.
Harvest it and prefer it for routing.

**ADBC** is the one abstraction that could collapse six harvesters into one code path: Arrow-native
database access that can execute SQL **and Substrait**, query catalogs, inspect table schemas, and
eliminate data copies, with bindings for C/C++, C#, Go, Java, Python, R, Ruby, Rust
([ADBC docs](https://arrow.apache.org/adbc/current/index.html)). Its **driver list is n.a.** on
that page — verify per-engine driver maturity, especially Oracle and MSSQL, before committing.
Ship the per-dialect harvesters first; treat ADBC as a consolidation opportunity, not a
foundation.

## Profiling — take the optimizer's statistics, do not scan

Oracle's `NUM_DISTINCT`, `NUM_NULLS`, `LOW_VALUE`, `HIGH_VALUE`, and `DENSITY` are **free
profiling data already computed by `DBMS_STATS`**
([Oracle docs](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html)).
Harvest them instead of running your own expensive scans wherever optimizer statistics are
current. The docs flag several of these as retained "for backward compatibility with Oracle7,"
with the authoritative data elsewhere — so treat them as hints, not ground truth
([Oracle docs](https://docs.oracle.com/en/database/oracle/oracle-database/19/refrn/ALL_TAB_COLUMNS.html)).

Store per column: distinct counts, null fractions, min/max, and a bounded set of top values.
LinkedIn ships `Top Values` as a first-class node attribute
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

A full table scan for profiling on a client production warehouse is an availability incident
waiting to happen. Optimizer statistics first; sampled scans only with explicit tenant opt-in and
a bytes/time cap.

## Join inference when FKs are not declared

The published technique that works at scale is **parse the query log**. LinkedIn builds its usage
index by parsing **Trino EXPLAIN plan JSON** to extract fully-qualified tables and columns **and
join conditions** ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). For non-Trino
engines, parse historical SQL with SQLGlot and walk the AST for join predicates; SQLGlot's
`lineage()` gives column-level provenance through views and CTEs
([SQLGlot lineage docs](https://sqlglot.com/sqlglot/lineage.html)).

Where declared constraints exist, harvest them: Snowflake exposes `TABLE_CONSTRAINTS` and
`REFERENTIAL_CONSTRAINTS` ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema));
Oracle exposes constraint views in the data dictionary (specific view page not fetched: **n.a.**).

Statistical/name-based FK inference (name-pattern matching plus inclusion-dependency testing on
sampled values) is standard practice, but **no published accuracy evidence** was found: **n.a.**
Therefore: treat inferred joins as *suggestions with confidence*, surface them for human
certification, and **never let an inferred join reach a governed metric**. dbt's design choice is
instructive — MetricFlow captures identifier types but deliberately does not capture arbitrary
join logic, specifically to avoid fan-out and chasm joins
([dbt MetricFlow docs](https://docs.getdbt.com/docs/build/about-metricflow)). Cube's framing is
the warning: the join graph is "a minefield" of fan-out, slowly-changing dimensions, and multiple
"customer" tables, and the wrong grain **silently double-counts**
([Cube](https://cube.dev/articles/semantic-layer-for-ai-agents-2026)). Looker's mitigation for
fan-out is **symmetric aggregates**
([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)).

## Refresh cadence

LinkedIn's published cadence ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)):

| Index | Refresh |
|---|---|
| Table / column metadata | Weekly |
| Usage index | Weekly |
| Cluster index | Weekly |
| Example queries | As needed |
| Domain knowledge | **Instant** |

Domain knowledge is instant because it is the cheapest, highest-leverage correction channel: when
an analyst says "`rev_net_usd` is the one people mean by revenue," that must be live on the next
question, not next week.

Two additions from the engine docs:

- Snowflake INFORMATION_SCHEMA has **no consistency guarantee under concurrent DDL**
  ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)), so a harvest is
  always a snapshot. **Version the catalog, and make the validation layer the authority at query
  time rather than the catalog.** A stale catalog must produce a validation failure, not a wrong
  answer.
- Snowflake's account-level history table functions have short retention — `QUERY_HISTORY`
  **7 days**, most others **14 days**, storage metering **6 months**
  ([Snowflake docs](https://docs.snowflake.com/en/sql-reference/info-schema)). If you want a query
  log for join inference and exemplar mining, you must **copy it out on a schedule at least as
  often as the retention window**. Miss this and the join-inference corpus is permanently gone.

## Exemplar retrieval

DAIL-SQL is the systematic study of question representation, example selection, and example
organization, reaching **86.6% EX on Spider** with explicit token-efficiency attention, and also
evaluating open-source LLMs with SFT ([arXiv 2308.15363](https://arxiv.org/abs/2308.15363)).
XiYan-SQL uses NER-based example selection
([arXiv 2411.08599](https://arxiv.org/abs/2411.08599)). Google retrieves "examples of similar
SQL" and "samples of recent queries that a user has run against the same datasets"
([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).
LinkedIn indexes example queries and refreshes them "as-needed"
([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

**Effect-size caution:** DAIL-SQL's 86.6% is on Spider; DAIL-SQL scores **3.6% on BEAVER**
([BEAVER paper](https://arxiv.org/html/2409.02038v3)) and **2.20% on Spider 2.0-Snow**
([Spider 2.0 site](https://spider2-sql.github.io/)). Exemplars help; they do not survive a scale
change on their own. Budget for exemplars as a second-order gain on top of retrieval, never as a
substitute for it.

## The mitigation ledger — what actually moves the number

| Intervention | Measured delta | Source |
|---|---|---|
| Hierarchical retrieval + rankers + fixer (full config vs schemas-only) | score **9% → 49%**; schema hallucination **23% → 1%**; compilation errors **34% → 4%** | ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)) |
| Rankers + fixer removed | compilation 96% → 66%; valid tables/columns 99% → 77% | ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)) |
| CHESS table-selection stage | **+6.12%** | ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)) |
| CHESS revision node | **+6.80%** | ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)) |
| Selective retrieval vs naive context augmentation | **+4.76% EX** | ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)) |
| LSH value index vs on-the-fly edit distance | **~5 min → ~5 sec** | ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)) |
| Knowledge-graph grounding vs raw SQL schema (GPT-4, insurance) | **16% → 54%** | ([arXiv 2311.07509](https://arxiv.org/abs/2311.07509)) |
| Authored context added to BigQuery NL2SQL | **30% → 80%** | ([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)) |
| Semantic-layer routing vs text-to-SQL, same questions | 90.0 → 98.2 and 84.1 → 100.0 | ([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)) |
| NL2LookML vs NL2SQL, same dataset | 97% vs 80% | ([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)) |
| Cortex Analyst vs GPT-4o, same 150 questions | 90%+ vs **51%** | ([Snowflake](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)) |
| Self-consistency on Spider (string-level) | **+0.4 pt** (86.2 → 86.6) | ([Spider leaderboard](https://yale-lily.github.io/spider)) |

Read the last row against all the others. Every large delta comes from grounding, retrieval, or
routing. Prompt-level tricks are worth fractions of a point.
