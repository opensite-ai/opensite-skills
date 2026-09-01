# The Validation Ladder, Candidate Selection, and Production Evaluation

Read this when implementing the compiler/validator, the repair loop, the candidate selector, or
the production quality metrics. This is the layer that makes "never hallucinate a table or column"
a property of the system rather than a hope about the model.

## The one rule

**The model chooses; deterministic code decides.** No SQL reaches an engine, and no answer reaches
a user, unless every identifier in it resolved against the harvested catalog and the engine itself
accepted the statement without executing it.

## Trap first: SQLGlot is not a validator

From SQLGlot's own docs, verbatim: "The parser is intentionally lenient. It can accept queries
that a real engine would reject. SQLGlot is a transpiler, not a validator. A query that parses
successfully may still fail at execution time." ([SQLGlot docs](https://sqlglot.com/sqlglot.html))

Two consequences that engineers get wrong:

1. `parse_one()` succeeding proves nothing about identifier existence. Identifier validation is
   the job of `qualify`, with an explicit schema.
2. Unsupported dialect translations only **warn** by default. You must set
   `unsupported_level=sqlglot.ErrorLevel.RAISE` to get an `UnsupportedError`
   ([SQLGlot docs](https://sqlglot.com/sqlglot.html)). A silent downgrade of a window function
   across dialects is exactly the failure that produces a plausible wrong number.

SQLGlot supports **over 30 dialects**. Official: Athena, BigQuery, ClickHouse, Databricks, DuckDB,
Hive, MySQL, Oracle, Postgres, Presto, Redshift, Snowflake, Spark, SQLite, StarRocks, Tableau,
Trino, TSQL. Community: DAX, Doris, Dremio, Drill, Druid, Dune, Exasol, Fabric, Materialize, PRQL,
RisingWave, SingleStore, Solr, Teradata. Plugin dialects since v28.6.0: YDB, MaxCompute
([SQLGlot docs](https://sqlglot.com/sqlglot.html)). API surface used here: `transpile(sql, read=,
write=)`, `parse`, `parse_one`, `tokenize`, AST diff (Insert/Remove/Move/Update/Keep), and
`optimize()` which accepts a schema ([SQLGlot docs](https://sqlglot.com/sqlglot.html)).

`ParseError` carries structured `e.errors` with description, line, col, start_context, highlight,
end_context — surface all of it to the repair loop
([SQLGlot docs](https://sqlglot.com/sqlglot.html)). Custom dialects come from subclassing
`Dialect` (which does **not** work with the `sqlglot[c]` mypyc build) or from entry-point plugins
under `sqlglot.dialects` ([SQLGlot docs](https://sqlglot.com/sqlglot.html)) — if you ship the
mypyc build for speed, you have foreclosed subclass-based custom dialects. Decide once, test it.

## The 7 rungs

Order is cheapest-first. Each rung catches a distinct failure class. A candidate must clear all
seven before execution.

### Rung 1 — Parse in the target dialect

`sqlglot.parse_one(sql, read=dialect)`. Catches syntax errors with line and column
([SQLGlot docs](https://sqlglot.com/sqlglot.html)).

```python
import sqlglot
from sqlglot.errors import ParseError

try:
    ast = sqlglot.parse_one(sql, read=dialect)
except ParseError as e:
    return Reject("parse", [
        {"msg": d["description"], "line": d["line"], "col": d["col"]} for d in e.errors
    ])
```

### Rung 2 — AST statement allowlist

Assert the root expression is a `Select`; reject everything else. This is a *parse-time* check on
a lenient parser, so it is a usability guard, **not** a security boundary.

```python
from sqlglot import exp

if not isinstance(ast, exp.Select) and not (
    isinstance(ast, exp.Subquery) or isinstance(ast, exp.Union)
):
    return Reject("statement_type", [f"root node {type(ast).__name__} not allowed"])
# also reject DDL/DML anywhere in the tree, including inside CTEs
for node in ast.walk():
    if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop,
                         exp.Create, exp.Alter, exp.TruncateTable, exp.Command)):
        return Reject("statement_type", [f"forbidden node {type(node).__name__}"])
```

`exp.Command` matters: SQLGlot parses statements it does not model into a generic `Command` node,
which is precisely where an unmodeled `GRANT` or vendor procedure call would hide.

Cube's argument applies directly and is the reason this rung is not the boundary: "post-hoc SQL
linting is brittle because SQL can reach data via subqueries, CTEs, views, and joins"
([Cube](https://cube.dev/articles/semantic-layer-for-ai-agents-2026)). The boundary is the
read-only role (see `references/safety-and-governance.md`).

### Rung 3 — `qualify` against the harvested catalog

This is the anti-hallucination rung, and it runs **without touching the database**.

Signature ([SQLGlot qualify docs](https://sqlglot.com/sqlglot/optimizer/qualify.html)):

```
qualify(expression, dialect, db, catalog, schema, expand_alias_refs=True, expand_stars=True,
        infer_schema=None, isolate_tables=False, qualify_columns=True,
        allow_partial_qualification=False, validate_qualify_columns=True,
        quote_identifiers=True, identify=True, infer_csv_schemas=False)
```

`schema` accepts a dict like `{"tbl": {"col": "INT"}}`, and `validate_qualify_columns=True`
invokes `validate_qualify_columns_func(expression)`
([SQLGlot qualify docs](https://sqlglot.com/sqlglot/optimizer/qualify.html)).

```python
from sqlglot.optimizer.qualify import qualify

qualified = qualify(
    ast,
    dialect=dialect,
    schema=catalog_slice,              # exactly the retrieved slice, nothing wider
    validate_qualify_columns=True,
    allow_partial_qualification=False,
    infer_schema=False,                # never let it invent a schema
)
```

Non-negotiable settings: `validate_qualify_columns=True`, `allow_partial_qualification=False`,
`infer_schema=False`. `infer_schema` left at its default is how an unknown table quietly becomes
an "inferred" one.

**Pin the exception empirically.** The exact exception class raised for an unresolvable column is
**n.a.** on the qualify docs page
([SQLGlot qualify docs](https://sqlglot.com/sqlglot/optimizer/qualify.html)). Write a test that
asserts on the concrete class and message for your pinned SQLGlot version, and treat a SQLGlot
upgrade that changes it as a breaking change.

```python
def test_qualify_rejects_unknown_column():
    schema = {"orders": {"id": "INT", "total": "DECIMAL"}}
    with pytest.raises(Exception) as ei:      # narrow this to the observed class, then pin
        qualify(sqlglot.parse_one("SELECT nope FROM orders"),
                schema=schema, validate_qualify_columns=True,
                allow_partial_qualification=False, infer_schema=False)
    assert "nope" in str(ei.value)
```

### Rung 4 — Dialect transpile with `ErrorLevel.RAISE`

Only relevant if the model generates in a canonical dialect and you emit to the client's dialect.

```python
out = sqlglot.transpile(
    sql, read=canonical_dialect, write=target_dialect,
    unsupported_level=sqlglot.ErrorLevel.RAISE,
)[0]
```

Without `RAISE`, unsupported translations warn and continue
([SQLGlot docs](https://sqlglot.com/sqlglot.html)). The safer architecture is to generate directly
in the target dialect and use transpile only as a cross-check, since the client's engine — not
your canonical form — is the thing that has to be right.

### Rung 5 — Engine-side validation without execution

| Engine | Mechanism | Confirmed behavior |
|---|---|---|
| Trino | `EXPLAIN (TYPE VALIDATE) <stmt>` | Returns `Valid | true`; gives precise messages for syntax (`line 1:25: mismatched input 'SELET'`) and semantics (`line 1:15: Table 'tpch.tiny.nations' does not exist`) ([Trino EXPLAIN docs](https://trino.io/docs/current/sql/explain.html)) |
| BigQuery | **dry run** | Validates the query and estimates bytes processed, does **not** use query slots and does **not** incur charges. `bq query --dry_run` prints "Query successfully validated. Assuming the tables are not modified, running this query will process 10918 bytes of data." REST sets `dryRun: true` in `JobConfiguration`; clients set `QueryJobConfig(dry_run=True)` / `setDryRun(true)` / `q.DryRun = true`; read the estimate from `total_bytes_processed` / `statistics.getTotalBytesProcessed()` / `status.Statistics.TotalBytesProcessed` ([BigQuery docs](https://cloud.google.com/bigquery/docs/running-queries)) |
| Postgres / MySQL / MSSQL / Oracle / Snowflake | `PREPARE` / `EXPLAIN` inside an aborted read-only transaction | **Exact per-engine no-execute validation semantics: n.a.** — verify each empirically and write a per-dialect conformance test. Do not assume `EXPLAIN` is side-effect-free or non-executing on every engine |

The `n.a.` row is a real gap, not a formality. For each of the six target dialects, the
per-dialect adapter must ship a test proving that its "validate" call (a) rejects an unknown
table, (b) rejects an unknown column, and (c) does not materialize rows.

### Rung 6 — Independent catalog hallucination check

Extract every table and column reference from the qualified AST and check each against the index
as a **set operation**. This is not redundant with rung 5.

LinkedIn runs Trino `EXPLAIN` in VALIDATE mode **at most twice**, *plus* a separate validator that
checks every extracted table and column against the index — specifically because "Trino EXPLAIN
returns one error at a time" ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).

Engine validation is a **serial oracle**: one error per round trip. Catalog validation is a **set
operation**: every bad identifier in one pass. The repair loop needs the complete list, or you
burn your retry budget fixing errors one at a time.

### Rung 7 — Researcher / repair dispatch

LinkedIn dispatches a Researcher Agent (gpt-4o-mini) to search for tables similar to the
hallucinated ones ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). A hallucinated
identifier is usually a near-miss on a real one, so a similarity lookup over the catalog turns a
hard failure into a repairable one.

Google's guidance corroborates the whole ladder: "non-AI techniques, including query parsing and
dry runs of generated SQL, complement model-based workflows… providing a clear, deterministic
signal when the LLM has missed something crucial," with the error signal passed back for a second
pass ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).

## Repair loop policy

- **Cap at 2 retries.** That is the published production choice
  ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
- **Feed each retry the complete error list** from catalog validation, not one engine error at a
  time ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
- CHESS's revision node consumes schema + question + candidate SQL + **execution result**, and
  corrects logical, syntactic, and execution errors. Removing it costs **6.80%**
  ([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)).
- **Know the ceiling.** BIRD-CRITIC shows O3-Mini repairing only **38.87% (Postgres) / 33.33%
  (multi-dialect)** of real SQL issues
  ([arXiv 2506.18951v1](https://arxiv.org/html/2506.18951v1)). Repair loops fix syntax and
  identifiers reliably; they do not fix wrong semantics. A third retry buys noise and latency.

## Grammar-constrained decoding — what it can and cannot do

**PICARD** constrains autoregressive decoders through **incremental parsing**, rejecting
inadmissible tokens at each decoding step, and "transforms fine-tuned T5 models with passable
performance into state-of-the-art solutions" on Spider and CoSQL
([arXiv 2109.05093](https://arxiv.org/abs/2109.05093)). Exact numbers on that abstract page:
**n.a.**; the Spider leaderboard shows Graphix-3B+PICARD at 74.0 exact-set-match on test
([Spider leaderboard](https://yale-lily.github.io/spider)).

**vLLM + xgrammar can enforce a SQL grammar.** vLLM's structured-outputs backends are `xgrammar`
and `guidance` (with `outlines` and `lm-format-enforcer` also referenced for regex syntax),
selected via `--structured-outputs-config.backend`, default `auto`. Constraint types: `choice`,
`regex`, `json`, `grammar` (context-free EBNF), `structural_tag`. The docs explicitly state EBNF
grammar support "allows users to define complete languages such as SQL queries" and ship a
`simplified_sql_grammar` example (`root ::= select_statement`, …) passed as
`extra_body={"structured_outputs": {"grammar": simplified_sql_grammar}}`, or offline via
`StructuredOutputsParams` in `SamplingParams`. The docs call `grammar` "probably the most
difficult structured-output option to use, but is powerful"
([vLLM structured outputs docs](https://docs.vllm.ai/en/latest/features/structured_outputs.html)).
vLLM's documented xgrammar fallback behavior, Lark support, and stated grammar limitations:
**n.a.** on that page.

XGrammar's own EBNF documentation resolves the practical questions
([XGrammar EBNF docs](https://xgrammar.mlc.ai/docs/defining_structures/ebnf_grammar.html)):

- **Left recursion is supported** (`root ::= root "a" | "a"` is a working example) — which matters,
  because SQL expression grammars are naturally left-recursive.
- Full CFG machinery: sequences, alternatives, groups, `?`/`*`/`+`/`{n}`/`{n,m}`/`{n,}`, forward
  references.
- Per-rule budgets: `max_tokens`, `max_chars` (Unicode codepoints, 0-2,147,483,647), plus
  `capture`, `lazy`, `temperature`.
- Macros: `Regex`, `Substring`, `TagDispatch`, `Token`, `ExcludeToken`, `TokenTagDispatch`.
- **Real limitations:** regex shorthand `\d`, `\w`, `\s` are rejected inside character classes;
  `x{,4}` is invalid; two repetition operators cannot be stacked (`"a"++`); `suffix=`/`stop=` are
  not accepted in hand-written EBNF (author them through the Lark frontend); no public
  registration interface for custom macros (adding one requires C++ changes); `lazy` bodies must
  normalize to a single terminal-like form.

**The load-bearing assessment.** A CFG guarantees output is *syntactically* valid SQL. It
**cannot** guarantee the identifiers exist, because a context-free grammar cannot express "this
column belongs to a table in the FROM clause." You could compile a per-request grammar enumerating
the retrieved table and column names as literal alternatives — that *would* make identifier
hallucination structurally impossible — but you pay grammar compilation cost on every request, and
it still does not constrain correlated usage (right column, wrong table's alias).

Practical stance: **grammar constraints for shape, `qualify` against the catalog for identifiers,
execution for semantics.** Do not spend the budget making the grammar smart.

## Alternatives to SQLGlot for real validation

**Apache Calcite** is a dynamic data management framework that **omits data storage, data
processing algorithms, and a metadata repository**. Its query parser, validator, and optimizer are
all described as complete; it does cost-based optimization combining user-defined and built-in
rules and operators; it has an adapter framework (the CSV adapter in `example/csv` is the
documented template, plus a JDBC adapter) and **pushes JOIN and GROUP BY down to the source
database**; local and remote JDBC drivers are provided via Avatica
([Calcite docs](https://calcite.apache.org/docs/)). SQL coverage explicitly includes GROUPING
SETS, COUNT(DISTINCT), FILTER, correlated subqueries, windowed aggregates, UNION/INTERSECT/MINUS,
and PostgreSQL-style LIMIT ([Calcite docs](https://calcite.apache.org/docs/)). A named dialect
list is **n.a.** on that page.

Practical read: Calcite gives you a **real validator** — unlike SQLGlot's lenient parser — if you
are willing to model each client schema into a Calcite `Schema`/`Table` and run on the JVM. That
is a serious engineering commitment, and it is the only in-process option that will reject an
unknown column with the same rigor as an engine. Do not adopt it to start; keep it as the
escalation path if `qualify` + engine dry-run proves insufficient in measurement.

**Substrait** is a cross-language specification for describing compute operations on structured
data, with serialized representations, a text form, and visualizers, explicitly to avoid N×N
system integrations; its documented ecosystem mentions Calcite, the Arrow C++ compute kernel,
Iceberg views, Spark, Trino, DataFusion, Postgres, Pandas, and SingleStore
([Substrait](https://substrait.io/)). No definitive implementation-maturity list (**n.a.**).
Assessment: promising as an internal plan IR, not a dependency to put on a production critical
path for six commercial dialects.

**Trino** as a federation layer: documented as "not a general-purpose relational database," not a
replacement for MySQL/PostgreSQL/Oracle, and not designed for OLTP; it targets distributed OLAP
queries over TB-PB and has been extended to relational databases and Cassandra
([Trino use cases](https://trino.io/docs/current/overview/use-cases.html)). The connector catalog
page returned no list when fetched: **n.a.**
([Trino connectors](https://trino.io/docs/current/connector.html)). Attractive because
`EXPLAIN (TYPE VALIDATE)` is a first-class validation primitive, but adding Trino makes it a new
production dependency and a new latency floor for every query — measure before adopting.

## Candidate generation and selection

Generate diverse candidates, then select over **executed** ones.

CHASE-SQL's three generators ([arXiv 2410.01943](https://arxiv.org/abs/2410.01943)):

1. divide-and-conquer decomposition in a single LLM call,
2. chain-of-thought based on query **execution plans**,
3. instance-aware synthetic example generation,

then a **fine-tuned binary candidate-selection LLM using pairwise comparisons**, which the authors
state is "more robust over alternatives." BIRD test **73.0%**, dev 73.01%
([arXiv 2410.01943](https://arxiv.org/abs/2410.01943)).

MCS-SQL independently confirms: multiple prompts for schema linking, diverse candidates on the
refined schema, confidence filtering, then multiple-choice selection presented to the LLM. BIRD
**65.5%**, Spider **89.6%** ([arXiv 2405.07467](https://arxiv.org/abs/2405.07467)).

Inside CHESS's revision node, self-consistency across **three samples** selects the most frequent
SQL, and the authors note that even at temperature 0 different corrections appear across samples;
more revision samples produced additional gains
([CHESS via ar5iv](https://ar5iv.labs.arxiv.org/html/2405.16755)). Google describes generating
multiple queries per question, possibly with different prompting techniques or model variants, then
selecting the best candidate
([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).

**Selection rules.**

- Select over **executed** candidates, never over strings. String-level majority voting is worth
  +0.4 points on Spider (86.2 → 86.6,
  [Spider leaderboard](https://yale-lily.github.io/spider)) and is not a lever.
- A candidate that failed any validation rung is not a selection candidate. It is a rejected
  artifact recorded in the audit log.
- Result-set disagreement across candidates is the best cheap uncertainty proxy you have.

## Production evaluation without gold SQL

**STEF** — "Agent-Agnostic Evaluation of SQL Accuracy in Production Text-to-SQL Systems" — requires
**no gold SQL, no schema, and no execution**
([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1), 30 Apr 2026).

Inputs: original question `Q_u`, enriched question `Q_e`, generated SQL `S`, and an app rule JSON
`R_app`. Pipeline ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)):

1. **Semantic feature extraction** — a question-side spec (outputs, aggregations, filters,
   group_by) and a SQL-side spec (adds order_by, limit).
2. **Normalization** — alias resolution; case/whitespace; `ILIKE ≈ LIKE ≈` equality when
   non-wildcard; infers SUM/AVG/COUNT from "total"/"average"/"count of"; applies app column
   mappings.
3. **Specification alignment.**
4. **LLM semantic verdict** — Correct / Likely Correct / Potentially Incorrect / Incorrect, plus
   confidence γ ∈ [0,1].
5. **Rule injection.**

Scoring: **Φ = (B/10) × 100 × Γ**, where B = σ_filters + σ_verdict + δ_lenient (max 10).

| Component | Values |
|---|---|
| Filter scores | fully_applied 5; fully_applied_with_extras 4; partially_applied 3; not_applied 0 |
| Verdict scores | 5 / 3 / 2 / 0 |
| Confidence multiplier Γ | γ ≥ 0.85 → 1.0; 0.65 ≤ γ < 0.85 → 0.8; γ < 0.65 → 0.5 |

All from ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)).

**Gating thresholds:** 90-100 Excellent (automated production use); 75-90 Good; 50-75 Marginal
(escalate); <50 Poor ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)).

Benign-deviation tolerances: required GROUP BY; benign GROUP BY on WHERE-constrained constants;
sensible-default ORDER BY; high-cardinality safety LIMIT with recommended **λ_min = 1000**
([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)).

Reported production results ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)):

| Agent | Mean Φ | P90 | Coverage |
|---|---|---|---|
| Agent-A | 87.4 | 96.2 | 98.7% |
| Agent-B | 82.1 | 93.5 | 97.2% |
| Agent-C | 91.3 | 98.1 | 99.1% |

**Two caveats to state whenever you cite STEF.** (1) **Human-agreement correlation is n.a.** — the
paper only says thresholds were "calibrated against developer-assessed labels on a held-out
sample," which is weaker than a reported κ or r. (2) The authors concede accuracy **degrades for
deeply nested subqueries and window functions** and propose a hybrid symbolic-neural approach over
the SQL AST ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)) — i.e. it degrades on
exactly the query class this product must handle. Do not use Φ as the sole gate for
window-function or deeply-nested queries; require candidate agreement there too.

### Complementary measurement

- **LLM-as-judge with result-set matching.** lkr.dev's harness executes the golden query, executes
  both candidates, and compares result sets using **Jaccard similarity for value-based column
  mapping**, data-type coercion, floating-point tolerances, and equivalence "regardless of column
  names and row ordering"
  ([lkr.dev](https://www.lkr.dev/articles/benchmarking-semantic-layer-conversational-analytics/)).
  LinkedIn uses LLM-as-judge (gpt-4o-2024-05-13, temp 0) over a 133-question, 10-product-area
  benchmark with 167 ground-truth tables where **60% of questions have more than one valid
  response** ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Google uses
  LLM-as-a-judge "to reduce cost while still understanding performance on ambiguous and unclear
  tasks" ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).
- **Multiple-acceptable-gold-SQL.** Snowflake rejects plain execution accuracy because "one
  business question may have multiple correct SQL answers," instead running questions across many
  models, having humans select all correct queries into an acceptable-gold set, then scoring column
  precision/recall at a lenient threshold
  ([Snowflake](https://www.snowflake.com/en/blog/engineering/cortex-analyst-text-to-sql-accuracy-bi/)).
- **Cheap deterministic proxies computable on 100% of traffic:** **successful compilation rate**
  and **valid tables/columns rate** — 96% and 99% in LinkedIn's full config versus 88% and 77% in
  ablations ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). No judge, no gold SQL,
  and they move the moment retrieval or validation regresses. Alert on these.
- **Behavioral metrics.** LinkedIn tracks weekly active users (>300), share of sessions leading to
  pasted code (33%), ~20% week-over-week return rate, and user ratings (39% very good/excellent,
  95% at least "passes") ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)). Google
  "combines user metrics and offline evaluation metrics"
  ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).
- **Tooling:** IBM's Text-to-SQL Evaluation Toolkit (VLDB 2026) offers 12+ metrics including
  execution accuracy, syntactic equivalence, and LLM-as-judge
  ([IBM Research](https://research.ibm.com/publications/text-to-sql-evaluation-toolkit)); an
  LLM-based SQL-equivalence evaluation method is proposed in
  [arXiv 2506.09359](https://arxiv.org/pdf/2506.09359). Both found via search, pages not fetched —
  treat details as unverified.
- **Build a synthetic multi-dialect benchmark.** Google explicitly augments academic benchmarks
  with synthetic ones covering "broad real-world schemas and workloads, including multiple SQL
  engines and products, dialects, engine-specific features, queries, DDL, DML, administrative
  needs, common usage patterns, complex queries, and complex schemas," because academic benchmarks
  "can lack broad real-world schemas and workloads"
  ([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).
  For a six-dialect product this is not optional.

## Ambiguity detection

Ambiguity is a first-order accuracy problem, not a UX nicety. Google's canonical example: for
"What is the best selling shoe?" the system should ask "Would you like to see the shoes ordered by
order quantity or revenue?", and it "typically orchestrates LLM calls to first determine whether a
question can be answered using the available schema and data" before generating clarifying
questions. It also notes the right behavior differs by user: "a reasonable starting SQL query may
be useful for a technical analyst or developer, while precise and correct SQL is more important
for a less technical user"
([Google Cloud](https://cloud.google.com/blog/products/databases/techniques-for-improving-text-to-sql)).

| Work | Contribution |
|---|---|
| **AmbiSQL** (SIGMOD'26 demo) | Two-stage ambiguity identification plus iterative refinement; generates clarification questions and forwards the clarified rewrite to XiYan-SQL; demonstrated on 40 ambiguous queries from two real benchmarks ([arXiv 2508.15276v2](https://arxiv.org/html/2508.15276v2)) |
| **AMBROSIA** (Saparina & Lapata 2024) | 1,277 ambiguous questions, 2,965 SQL queries, 846 multi-table databases, 16 domains, covering **scope**, **attachment**, and **vagueness** ambiguity ([Edinburgh Research Explorer](https://www.research.ed.ac.uk/en/publications/ambrosia-a-benchmark-for-parsing-ambiguous-questions-into-databas/)) |
| **AmbiQT** | 3,000+ examples across four ambiguity types (column, table, join, …) with the LogicalBeam decoding method ([ar5iv 2310.13659](https://ar5iv.labs.arxiv.org/html/2310.13659)) |
| **Disambiguate First, Parse Later** | ([ar5iv 2502.18448](https://ar5iv.labs.arxiv.org/html/2502.18448)) |
| **PRACTIQ** | Ambiguous/unanswerable conversational dataset built with SQLGlot; oracle cell values boost ambiguity classification by **1.5%** ([arXiv 2410.11076v1](https://arxiv.org/html/2410.11076v1)) |
| **CLUES** (clinical) | Separates **ambiguity** from **instability** via a Schur complement; the high-ambiguity/high-instability regime holds **51% of errors while covering only 25% of queries** ([ar5iv 2602.12015](https://ar5iv.labs.arxiv.org/html/2602.12015)) |
| **FLEX** (NAACL 2025) | ([arXiv 2409.19014](https://arxiv.org/pdf/2409.19014), [repo](https://github.com/HeegyuKim/FLEX)) |

CLUES is the most actionable confidence-gating result available: a cheap two-axis score can isolate
half your errors into a quarter of your traffic
([ar5iv 2602.12015](https://ar5iv.labs.arxiv.org/html/2602.12015)). Build the two-axis score before
building anything fancier.

## Confidence gating — the concrete policy

Compose four independently sourced signals:

1. **Hard gate: catalog validity.** Any query whose identifiers do not resolve against the
   harvested catalog never reaches the user, regardless of model confidence. Target the published
   **99% valid-tables/columns** rate ([arXiv 2507.14372v1](https://arxiv.org/html/2507.14372v1)).
2. **Candidate agreement.** Execute N candidates read-only and compare result sets; pairwise
   selector confidence is the published ranking mechanism
   ([arXiv 2410.01943](https://arxiv.org/abs/2410.01943),
   [arXiv 2405.07467](https://arxiv.org/abs/2405.07467)).
3. **Spec-alignment score.** STEF's Φ with its 90 / 75 / 50 thresholds, honoring Γ
   ([arXiv 2604.28049v1](https://arxiv.org/html/2604.28049v1)).
4. **Ambiguity score.** Route high-ambiguity questions to clarification rather than generation
   ([arXiv 2508.15276v2](https://arxiv.org/html/2508.15276v2),
   [ar5iv 2602.12015](https://ar5iv.labs.arxiv.org/html/2602.12015)).

Then adopt the semantic layer's **failure semantics** for the whole system. dbt's central
operational claim is that text-to-SQL "fails silently" with plausible wrong numbers while the
semantic layer "fails loudly" by refusing
([dbt Labs](https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026)). This is
corroborated structurally by BEAVER's error taxonomy, where 46.8% of errors are
analytical/structural rather than syntactic
([BEAVER paper](https://arxiv.org/html/2409.02038v3)) — errors that look fine and return a number.

**A text-to-SQL product that cannot refuse is strictly worse than one that can, independent of its
mean accuracy.** Ship the refusal path before you ship the accuracy work.
