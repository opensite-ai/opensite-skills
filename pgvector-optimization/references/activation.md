# Activation Guide

## Best-Fit Tasks
- pgvector performance optimization: HNSW vs IVFFlat index selection and tuning, ef_search / m / ef_construction parameters, iterative scanning for filtered queries, scalar and binary quantization for memory reduction, and dimensionality compression. Embedding-model-agnostic — applies to any float32 vector workload.
- Best trigger phrase: vector search queries are slow, recall is poor, or index memory footprint is too large.

## Explicit Invocation
- `Use $pgvector-optimization when vector search queries are slow, recall is poor, or index memory footprint is too large.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
