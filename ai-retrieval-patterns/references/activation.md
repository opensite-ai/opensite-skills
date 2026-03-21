# Activation Guide

## Best-Fit Tasks
- Retrieval architecture for AI applications — choosing and combining vector RAG, PageIndex (vectorless PDF tree-search), and precision embedding models. Covers the decision framework for matching retrieval strategy to document type and query characteristics, Milvus collection design, hybrid two-stage pipelines, the EmbeddingProvider abstraction, and the routing layer that ties it all together.
- Best trigger phrase: building semantic search, RAG pipelines, document Q&A, or any system where retrieval strategy and embedding model choice affect answer quality.

## Explicit Invocation
- `Use $ai-retrieval-patterns when building semantic search, RAG pipelines, document Q&A, or any system where retrieval strategy and embedding model choice affect answer quality.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
