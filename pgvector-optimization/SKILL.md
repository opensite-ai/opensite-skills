---
name: pgvector-optimization
description: >
  pgvector performance optimization: HNSW vs IVFFlat index selection and tuning,
  ef_search / m / ef_construction parameters, iterative scanning for filtered
  queries, scalar and binary quantization for memory reduction, and
  dimensionality compression. Embedding-model-agnostic — applies to any float32
  vector workload. Use when vector search queries are slow, recall is poor, or
  index memory footprint is too large.
compatibility: >
  Requires PostgreSQL with pgvector or captured EXPLAIN output; SQL access
  improves tuning validation.
metadata:
  opensite-category: data
  opensite-scope: shared
  opensite-visibility: public
---
# pgvector Optimization

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.
- Template: [templates/index-tuning-record.md](templates/index-tuning-record.md)

pgvector with default settings gives you correct results but not optimal performance. The gap between default and tuned can be 10–100x in query speed and 4–8x in memory usage. This skill covers what to tune and when.

---

## HNSW vs. IVFFlat: Choosing the Right Index

| Dimension | HNSW | IVFFlat |
|-----------|------|---------|
| Build time | Slow (index built row by row) | Fast (one-shot build after data is loaded) |
| Build memory | High (entire graph in memory during build) | Lower |
| Query speed | Faster at equivalent recall | Slower; varies with `nprobes` |
| Incremental inserts | Excellent — inserts maintain graph structure | Poor — inserts don't update centroids |
| Recall at default settings | ~95% | ~85% |
| Use when | Production workloads with frequent inserts | Batch workloads, infrequently updated collections |

**Default recommendation**: Use HNSW unless your collection is static and you need faster build time.

---

## HNSW Index Parameters

```sql
-- Basic HNSW index
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Higher quality (more memory, slower build, better recall)
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 32, ef_construction = 200);
```

| Parameter | Default | Effect |
|-----------|---------|--------|
| `m` | 16 | Number of bi-directional links per node. Higher = better recall, more memory (~8 bytes × m × rows). Common values: 8 (memory-constrained), 16 (default), 32 (high-recall) |
| `ef_construction` | 64 | Candidate list size during index build. Higher = better index quality, slower build. Setting to 2× `m` or more is recommended |

### Memory Estimate for HNSW

```
Index memory ≈ (1.1 × m × 8 bytes × num_vectors) + (num_vectors × dimensions × 4 bytes)

Example: 1M vectors at 1024 dimensions, m=16:
  Graph:   1.1 × 16 × 8 × 1,000,000 = 140 MB
  Vectors: 1,000,000 × 1024 × 4     = 4 GB
  Total:   ~4.14 GB
```

---

## `ef_search`: Query-Time Recall vs. Speed Trade-off

`ef_search` (or `hnsw.ef_search` in pgvector) controls the candidate list size during query execution. Higher values search more candidates before returning results — better recall but slower queries.

```sql
-- Set for the current session
SET hnsw.ef_search = 40;   -- Default; fast but lower recall
SET hnsw.ef_search = 100;  -- Better recall; moderate cost
SET hnsw.ef_search = 200;  -- High recall; slower

-- Set as a server default (postgresql.conf or ALTER SYSTEM)
ALTER SYSTEM SET hnsw.ef_search = 100;
SELECT pg_reload_conf();
```

### Recall vs. ef_search Calibration

Measure recall by comparing ANN results against exact KNN results on a sample:

```sql
-- Exact KNN (no index — use for recall measurement only)
SET enable_indexscan = off;
SELECT id FROM items ORDER BY embedding <=> $1 LIMIT 10;
RESET enable_indexscan;

-- ANN with index
SET hnsw.ef_search = 40;
SELECT id FROM items ORDER BY embedding <=> $1 LIMIT 10;
```

Count the overlap between both result sets. `ef_search = 40` typically gives ~88–92% recall; `ef_search = 200` gives ~98%+.

**Rule of thumb**: `ef_search` should be at least as large as the `LIMIT` value in your query. For `LIMIT 10`, `ef_search = 40` gives adequate recall. For `LIMIT 100`, use `ef_search = 200`.

---

## IVFFlat Parameters

```sql
-- Build after loading data — centroids are computed from existing rows
CREATE INDEX ON items USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

| Parameter | Default | Effect |
|-----------|---------|--------|
| `lists` | 100 | Number of clusters. Recommended: `sqrt(num_rows)` for small sets; `rows / 1000` for large sets |
| `ivfflat.probes` | 1 | Number of clusters to search at query time. Higher = better recall, slower |

```sql
-- Set probes for the session
SET ivfflat.probes = 10;  -- Search 10 clusters; good recall for lists=100

-- Recommended: probes = sqrt(lists)
-- For lists=100: probes=10
-- For lists=1000: probes=32
```

**Critical**: IVFFlat requires data to be loaded before building the index. Building on an empty table gives meaningless centroids.

```sql
-- Load your data first
INSERT INTO items SELECT ...;

-- Then build the index
CREATE INDEX ON items USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

---

## Distance Metric Selection

pgvector supports three distance operators — the correct choice depends on how your embedding model was trained.

| Operator | Function | Use When |
|----------|----------|----------|
| `<=>` | Cosine distance | Most embedding models (BGE-M3, Qwen3, OpenAI) — normalized vectors |
| `<->` | L2 (Euclidean) distance | Models that explicitly use L2; also works for normalized vectors |
| `<#>` | Negative inner product | When you want inner product (equivalent to cosine for normalized vectors) |

```sql
-- Check if your vectors are normalized
SELECT AVG(vector_norm(embedding)) FROM items LIMIT 1000;
-- Should be ~1.0 for normalized vectors

-- If not normalized and your model uses cosine similarity, normalize at insert time
-- or use <-> with un-normalized vectors (results differ from cosine)
```

---

## Filtered Queries: The Recall Collapse Problem

Vector search with aggressive filters causes recall collapse — the ANN index returns candidates that are then filtered out, leaving fewer results than requested.

```sql
-- ❌ This may return fewer than 10 results if the filter is selective
SELECT id, embedding <=> $1 AS distance
FROM items
WHERE category = 'restaurant' AND city_id = 42
ORDER BY embedding <=> $1
LIMIT 10;
```

### Iterative Scanning (pgvector 0.7.0+)

pgvector 0.7.0 introduced iterative index scans — the engine fetches more candidates automatically until the LIMIT is satisfied.

```sql
-- Enable iterative scanning (requires pgvector 0.7.0+)
SET hnsw.iterative_scan = relaxed_order;
-- Options:
--   strict_order:   No iterative scan (default; may return < LIMIT results)
--   relaxed_order:  Iterative scan; results may not be in exact distance order
--   off:            Disabled

SELECT id FROM items
WHERE category = 'restaurant' AND city_id = 42
ORDER BY embedding <=> $1
LIMIT 10;
```

### Partial Index to Pre-Filter by Category

For high-cardinality filters that are known at index creation time:

```sql
-- Index only restaurant embeddings — queries filtering by category = 'restaurant'
-- will use this smaller, faster index
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)
WHERE category = 'restaurant';
```

### Two-Stage Retrieval for Selective Filters

When filters are too selective for the index to satisfy, broaden the ANN search and filter in application code:

```sql
-- Stage 1: Over-fetch from the vector index
SELECT id, description, category, city_id,
       embedding <=> $1 AS distance
FROM items
ORDER BY embedding <=> $1
LIMIT 200;  -- Fetch 200 candidates

-- Stage 2: Apply business filters in application code
-- Then re-rank the filtered subset
```

---

## Scalar Quantization: 4x Memory Reduction

Scalar quantization (SQ8) compresses each float32 (4 bytes) to int8 (1 byte) with ~1% recall penalty at equivalent `ef_search`. Available in pgvector 0.7.0+.

```sql
-- Full precision HNSW (baseline)
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Scalar quantization — 4x smaller, ~1% recall penalty
CREATE INDEX ON items USING hnsw (embedding vector_halfvec_ops)
WITH (m = 16, ef_construction = 64);

-- Or use the halfvec type directly (pgvector 0.7.0+)
ALTER TABLE items ADD COLUMN embedding_half halfvec(1024);
UPDATE items SET embedding_half = embedding::halfvec;
CREATE INDEX ON items USING hnsw (embedding_half vector_halfvec_ops);
```

### Memory Comparison

```
1M vectors at 1024 dimensions:
  float32:  1,000,000 × 1024 × 4 bytes = 4.0 GB
  halfvec:  1,000,000 × 1024 × 2 bytes = 2.0 GB
  int8:     1,000,000 × 1024 × 1 byte  = 1.0 GB (binary quantization)
```

---

## Binary Quantization: 32x Compression

Binary quantization (bit vectors) converts each dimension to a single bit. Only applicable for models that are explicitly trained for it (e.g., Qwen3 with binary quantization, Cohere Embed v3 with binary mode). Using it on models not trained for it produces poor recall.

```sql
-- Only use with models that explicitly support binary quantization
CREATE INDEX ON items USING hnsw (embedding bit_hamming_ops);

-- Query with bit vectors
SELECT id FROM items
ORDER BY embedding <~> $1::bit(1024)
LIMIT 10;
```

---

## Matryoshka Dimension Reduction

Matryoshka-trained models (Qwen3, OpenAI text-embedding-3-*, some others) maintain quality when dimensions are truncated. Use this to reduce index size without retraining.

```sql
-- Store at full 4096 dims, but truncate for the index
-- (Qwen3 Matryoshka: 4096 → 1024 → 256)

-- Option 1: Store truncated embedding at insert time
INSERT INTO items (description, embedding)
SELECT description, embedding[:1024]  -- Slice to first 1024 dimensions
FROM source;

-- Option 2: Index on a truncated expression (avoids storing twice)
CREATE INDEX ON items USING hnsw ((embedding[:1024]) vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- Query uses the same expression
SELECT id FROM items
ORDER BY embedding[:1024] <=> $1[:1024]
LIMIT 10;
```

**Important**: Only truncate dimensions from Matryoshka-trained models. Truncating a non-Matryoshka model's dimensions will degrade recall significantly.

---

## Monitoring Index Health

```sql
-- Check index size and configuration
SELECT
  i.relname AS index_name,
  pg_size_pretty(pg_relation_size(i.oid)) AS index_size,
  ix.indoption,
  am.amname AS access_method
FROM pg_index ix
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_am am ON am.oid = i.relam
WHERE ix.indrelid = 'items'::regclass;

-- Check if queries are using the index
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM items ORDER BY embedding <=> $1 LIMIT 10;
-- Look for "Index Scan using <index_name>" — not "Seq Scan"
```

### When the Planner Chooses a Seq Scan Over the Vector Index

```sql
-- pgvector's planner uses statistics on row counts and `max_scan_tuples`
-- If the table is small, the planner may choose Seq Scan

-- Check the current max_scan_tuples threshold
SHOW max_parallel_workers_per_gather;

-- Force index use for testing
SET enable_seqscan = off;
EXPLAIN (ANALYZE) SELECT id FROM items ORDER BY embedding <=> $1 LIMIT 10;
RESET enable_seqscan;
```

---

## Optimization Decision Tree

```
Recall is poor (< 90%) at current ef_search?
  └── Increase ef_search (try 2x current value)
  └── If still poor: increase m during index rebuild

Index build is too slow?
  └── Use IVFFlat (batch workload) or reduce ef_construction

Memory footprint too large?
  └── Use halfvec (2x reduction, ~1% recall loss)
  └── Use int8 quantization (4x reduction, ~2-3% recall loss)
  └── Use Matryoshka dimension reduction if model supports it

Filtered queries returning < LIMIT results?
  └── pgvector 0.7.0+: SET hnsw.iterative_scan = relaxed_order
  └── Create partial indexes for common filter predicates
  └── Over-fetch and filter in application code

Queries with many concurrent users are slow?
  └── Check HNSW index is in shared_buffers (pg_prewarm)
  └── Check ef_search is not set too high for throughput
  └── Consider read replicas for vector search workloads
```
