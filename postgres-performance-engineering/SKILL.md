---
name: postgres-performance-engineering
description: >
  PostgreSQL performance engineering beyond basic indexing: query plan
  instability, statistics staleness, EXPLAIN ANALYZE interpretation, GIN index
  pending list management, extended statistics for correlated columns, PgBouncer
  connection pooling modes, and autovacuum tuning. Use when investigating slow
  queries, debugging inconsistent query performance, or tuning PostgreSQL for
  high-write production workloads.
compatibility: >
  Requires PostgreSQL access or captured EXPLAIN and pg_stat output; shell
  access helps with psql-based inspection.
metadata:
  opensite-category: data
  opensite-scope: shared
  opensite-visibility: public

---
# PostgreSQL Performance Engineering

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.
- Template: [templates/explain-review.md](templates/explain-review.md)

Index creation is the beginning of PostgreSQL performance work, not the end. Production performance problems are usually about the query planner making wrong decisions — and the planner's decisions are only as good as its statistics.

---

## Reading `EXPLAIN ANALYZE` Correctly

```sql
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT r.*, COUNT(rv.id) as review_count
FROM restaurants r
LEFT JOIN reviews rv ON rv.restaurant_id = r.id
WHERE r.city_id = 5
GROUP BY r.id
ORDER BY review_count DESC
LIMIT 20;
```

### Anatomy of a Plan Node

```
Hash Join  (cost=1024.32..8432.10 rows=842 width=128) (actual time=12.4..89.3 rows=856 loops=1)
  Buffers: shared hit=1203 read=87 written=0
```

| Field | Meaning |
|-------|---------|
| `cost=0.00..N` | `startup_cost..total_cost` — planner's estimate |
| `rows=N` (plan) | Planner's row estimate |
| `rows=N` (actual) | Real rows processed |
| `loops=N` | Times this node ran (Nested Loop inner node runs once per outer row) |
| `actual time` | Milliseconds per loop |
| `shared hit=N` | Pages served from buffer cache (fast) |
| `shared read=N` | Pages read from disk (slow) |

**True node cost** = `actual time × loops`

### Diagnosing Plan Node Choice

| Planner Choice | Condition That Caused It | Check |
|----------------|-------------------------|-------|
| `Seq Scan` instead of `Index Scan` | Table is small, or index selectivity is low | Check row estimate accuracy; add partial index |
| `Hash Join` instead of `Nested Loop` | Large outer set | Usually correct; Nested Loop can be faster for small outer |
| `Sort` at top level | No index covers the ORDER BY | Add index matching the sort expression |
| `Hash Aggregate` with disk spill | `work_mem` too low | Increase `work_mem` for this session: `SET work_mem = '64MB'` |

---

## Statistics Staleness: The Root Cause of Most Plan Bugs

The planner's row estimates (`rows=N`) come from `pg_statistic` — table statistics gathered by `ANALYZE`. Stale statistics cause the planner to choose wrong join algorithms, wrong indexes, and wrong scan strategies.

### Detecting Stale Statistics

```sql
-- Compare estimated vs actual rows from EXPLAIN ANALYZE
-- If they differ by > 2x, statistics are stale

-- Check when a table was last analyzed
SELECT
  schemaname,
  tablename,
  last_analyze,
  last_autoanalyze,
  n_live_tup,
  n_dead_tup,
  n_mod_since_analyze
FROM pg_stat_user_tables
WHERE tablename = 'orders'
ORDER BY n_mod_since_analyze DESC;
```

If `n_mod_since_analyze` is large relative to `n_live_tup`, run `ANALYZE`:

```sql
-- Manual analyze (non-blocking)
ANALYZE orders;

-- Verbose output to see what it found
ANALYZE VERBOSE orders;
```

### Autovacuum Tuning for High-Write Tables

The default autovacuum trigger threshold is `50 rows + 20% of table size`. For a 10M-row table, autovacuum doesn't run until 2,000,050 rows change. Statistics stay stale under heavy write load.

```sql
-- Set per-table autovacuum thresholds for high-write tables
ALTER TABLE orders SET (
  autovacuum_analyze_scale_factor = 0.01,   -- Trigger at 1% changed (default: 20%)
  autovacuum_analyze_threshold    = 1000,   -- Or 1000 rows changed (default: 50)
  autovacuum_vacuum_scale_factor  = 0.01,
  autovacuum_vacuum_threshold     = 1000
);
```

---

## Query Plan Instability

The same query with the same data can produce different plans across sessions or after a configuration change. This is almost always caused by:

1. **Statistics staleness** — fixed by `ANALYZE` and autovacuum tuning
2. **`work_mem` variance** — different sessions have different `work_mem`, causing different join strategies
3. **Statistics not covering correlated columns** — planner underestimates row counts for multi-column predicates

### Forcing Plan Stability for Debugging

```sql
-- Disable specific plan strategies to see if performance improves
SET enable_nestloop = off;    -- Force Hash Join or Merge Join
SET enable_seqscan  = off;    -- Force index scan (if one exists)

-- Run the query and compare
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;

-- Always reset after testing
RESET enable_nestloop;
RESET enable_seqscan;
```

**Never set these globally in production.** They are diagnostic tools only.

---

## Extended Statistics for Correlated Columns

PostgreSQL's per-column statistics assume columns are independent. For tables where columns are highly correlated (city_id + neighborhood_id, status + status_code), the planner underestimates selectivity.

```sql
-- Check correlation between columns
SELECT correlation
FROM pg_stats
WHERE tablename = 'restaurants' AND attname = 'city_id';

-- Create extended statistics to teach the planner about correlations
CREATE STATISTICS restaurants_city_neighborhood (ndistinct, dependencies)
ON city_id, neighborhood_id
FROM restaurants;

-- Must ANALYZE after creating extended statistics
ANALYZE restaurants;

-- Verify it's being used
EXPLAIN (ANALYZE) SELECT * FROM restaurants WHERE city_id = 5 AND neighborhood_id = 12;
-- Look for "Statistics objects: restaurants_city_neighborhood" in the output
```

---

## GIN Index Pending List

GIN (Generalized Inverted Index) indexes, used for full-text search, JSONB, and array operators, use a "pending list" — a small accumulation buffer that gets merged into the main index periodically.

```sql
-- Check GIN index pending list size
SELECT
  schemaname,
  tablename,
  indexname,
  pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE indexdef LIKE '%gin%';

-- If queries against GIN-indexed columns are slow under write load:
-- The pending list may be large (requires full scan of pending list)

-- Manually clean the pending list (non-blocking, but takes time)
SELECT gin_clean_pending_list('index_name'::regclass);
```

### GIN Pending List Tuning

```sql
-- Increase fastupdate threshold to reduce merge frequency under high writes
ALTER INDEX index_restaurants_on_search_vector SET (fastupdate = on, gin_pending_list_limit = 8192);

-- Disable fastupdate on indexes where query consistency matters more than write speed
ALTER INDEX index_critical_search SET (fastupdate = off);
```

---

## Partial Indexes

Partial indexes index a subset of rows. They're smaller, faster, and have higher selectivity than full indexes for queries with constant predicates.

```sql
-- Only index pending orders — 95% of queries target pending orders
CREATE INDEX CONCURRENTLY idx_orders_pending ON orders (created_at)
WHERE status = 'pending';

-- Only active restaurants in the main app query path
CREATE INDEX CONCURRENTLY idx_restaurants_active_city ON restaurants (city_id, name)
WHERE active = true AND deleted_at IS NULL;
```

The query planner will only use these indexes when the query's WHERE clause includes the predicate from the index definition.

```sql
-- Uses idx_orders_pending
SELECT * FROM orders WHERE status = 'pending' AND created_at > NOW() - INTERVAL '7 days';

-- Does NOT use it (status not constrained to 'pending')
SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '7 days';
```

---

## Connection Pooling: PgBouncer Session vs. Transaction Mode

PgBouncer is the standard connection pooler for PostgreSQL. Choosing the wrong mode causes subtle application failures.

| Mode | Server connection held | Compatible with |
|------|------------------------|-----------------|
| Session | For entire client session | Everything — SET variables, LISTEN, prepared statements |
| Transaction | Only during a transaction | Most ORMs; NOT compatible with `SET`, advisory locks held between transactions, `LISTEN` |
| Statement | Only during one statement | Very limited use cases |

### Transaction Mode Gotchas

**SET is scoped to a connection** — in transaction mode, the connection changes between transactions, making per-session `SET` unreliable:

```ruby
# ❌ Will silently fail with PgBouncer transaction mode
ActiveRecord::Base.connection.execute("SET search_path TO tenant_123, public")
# This SET applies to whatever server connection is assigned to this transaction.
# The next transaction may get a different server connection.

# ✅ Use schema-qualified queries or set search_path at connection setup level
```

**Advisory locks in transaction mode** — `pg_advisory_lock` is session-scoped. In transaction mode, the lock is released when the connection is returned to the pool, not when you call `pg_advisory_unlock`.

```ruby
# ❌ Advisory lock appears to work but is released when transaction ends
ActiveRecord::Base.connection.execute("SELECT pg_advisory_lock(42)")

# ✅ Use transaction-scoped advisory locks in transaction mode
ActiveRecord::Base.connection.execute("SELECT pg_advisory_xact_lock(42)")
# Automatically released at end of transaction — compatible with pool reuse
```

### PgBouncer Pool Size Formula

```
max_server_connections = (DB_MAX_CONNECTIONS * 0.9)  # Leave 10% for direct access
pool_size_per_database = max_server_connections / num_databases

# Example: PostgreSQL max_connections=100, 2 databases
# pool_size = 90 / 2 = 45 connections per database
# PgBouncer can multiplex 500+ clients onto these 45 server connections in transaction mode
```

---

## `pg_stat_statements`: Finding the Expensive Queries

```sql
-- Enable the extension (requires superuser; add to shared_preload_libraries)
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Top 10 queries by total time
SELECT
  LEFT(query, 80) as query_preview,
  calls,
  ROUND((total_exec_time / 1000)::numeric, 2) as total_sec,
  ROUND((mean_exec_time)::numeric, 2) as mean_ms,
  ROUND((stddev_exec_time)::numeric, 2) as stddev_ms,
  rows
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat%'
ORDER BY total_exec_time DESC
LIMIT 10;

-- Queries with high variance (inconsistent performance = plan instability)
SELECT
  LEFT(query, 80) as query_preview,
  calls,
  ROUND((mean_exec_time)::numeric, 2) as mean_ms,
  ROUND((stddev_exec_time / mean_exec_time * 100)::numeric, 1) as cv_percent
FROM pg_stat_statements
WHERE calls > 100 AND mean_exec_time > 10
ORDER BY (stddev_exec_time / mean_exec_time) DESC
LIMIT 20;
```

High coefficient of variation (CV%) on a frequently-called query is the signature of query plan instability.

---

## Dead Tuple Bloat

Dead tuples from `UPDATE` and `DELETE` operations are not reclaimed immediately — they accumulate until `VACUUM` runs. High dead tuple counts slow full scans and can cause table bloat.

```sql
-- Check dead tuple count
SELECT
  relname,
  n_live_tup,
  n_dead_tup,
  ROUND(n_dead_tup::numeric / NULLIF(n_live_tup + n_dead_tup, 0) * 100, 1) as dead_pct,
  last_vacuum,
  last_autovacuum
FROM pg_stat_user_tables
ORDER BY dead_pct DESC NULLS LAST;

-- Manual VACUUM (non-blocking — doesn't return space to OS but reclaims for reuse)
VACUUM orders;

-- VACUUM FULL — reclaims space to OS but requires exclusive lock (use with extreme caution)
-- Only appropriate for tables with >50% bloat during a maintenance window
VACUUM FULL orders;
```

---

## Performance Tuning Checklist

When investigating a slow query or endpoint:

- [ ] Run `EXPLAIN (ANALYZE, BUFFERS)` — never guess, always measure
- [ ] Check estimated vs actual row counts — discrepancy > 2x → run `ANALYZE table_name`
- [ ] Check `last_autoanalyze` in `pg_stat_user_tables` — if stale, tune autovacuum thresholds
- [ ] Any `Seq Scan` on table > 10K rows → consider index; check if partial index applies
- [ ] Multi-column predicates returning unexpected row counts → create extended statistics
- [ ] High-write table with GIN index → check pending list size; tune `gin_pending_list_limit`
- [ ] Using PgBouncer transaction mode → no session-scoped `SET`; use `pg_advisory_xact_lock` not `pg_advisory_lock`
- [ ] High CV% from `pg_stat_statements` → query plan instability → check statistics + correlation
- [ ] Dead tuple % > 20% → tune autovacuum or run manual `VACUUM`
