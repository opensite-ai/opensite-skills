---
name: ai-retrieval-patterns
description: >
  Retrieval architecture for AI applications — choosing and combining vector
  RAG, PageIndex (vectorless PDF tree-search), and precision embedding models.
  Covers the decision framework for matching retrieval strategy to document type
  and query characteristics, Milvus collection design, hybrid two-stage
  pipelines, the EmbeddingProvider abstraction, and the routing layer that ties
  it all together. Use when building semantic search, RAG pipelines, document
  Q&A, or any system where retrieval strategy and embedding model choice affect
  answer quality.
compatibility: >
  Best with access to retrieval code, Milvus schemas, and benchmark notes;
  pgvector or Milvus access helps for live tuning validation.
metadata:
  opensite-category: ai
  opensite-scope: shared
  opensite-visibility: public
---
# AI Retrieval Patterns

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.
- Template: [templates/retrieval-decision-record.md](templates/retrieval-decision-record.md)

Retrieval is not a solved problem. Picking the wrong strategy wastes compute, degrades answer quality, and creates maintenance debt. Question every default. This skill establishes a decision framework for choosing and combining retrieval strategies.

---

## Strategy Decision Tree

```
Is the source a long, structured PDF (financial filing, manual, regulatory doc)?
  └── YES: Does it have a meaningful Table of Contents or section hierarchy?
        └── YES → PageIndex (vectorless tree-search)
              └── Also need broad keyword recall? → Vector shortlist → PageIndex deep-dive
        └── NO  → Standard vector RAG
  └── NO: Short document / general text?
        └── Is very high-precision semantic matching required?
              └── YES → Qwen3-Embedding-8B (dense only, MTEB #1)
              └── NO, multilingual or general purpose → BGE-M3 hybrid (dense+sparse+ColBERT)
```

### When Each Strategy Wins

| Scenario | Best Strategy | Reason |
|----------|--------------|--------|
| Long structured PDFs (10-K, FDA filings, ISO standards) | PageIndex | No chunking; LLM navigates TOC; 98.7% FinanceBench accuracy |
| Short documents, reviews, multilingual text | BGE-M3 hybrid RAG | Sparse+dense+ColBERT for recall at 1.1GB VRAM |
| Media asset selection, fine-grained semantic matching | Qwen3-Embedding-8B | #1 MTEB multilingual (75.22), superior precision |
| Mixed corpus (PDFs + short text) | Hybrid: vector shortlist → PageIndex | BGE-M3 for recall, PageIndex for precision on PDFs |
| Real-time search, latency < 50ms | BGE-M3 dense-only or Qwen3 Matryoshka 256d | Compressed dimensions reduce HNSW search time |

---

## Standard Vector RAG with BGE-M3

BGE-M3 (BAAI, Apache 2.0) produces three vector types from a single forward pass — this is its key advantage:

- **Dense vector** (1024 dims): Semantic similarity
- **Sparse vector** (variable dims): Lexical recall — captures exact terms, prevents semantic drift
- **ColBERT vectors** (token-level): Late interaction for precision reranking

Use BGE-M3 for general-purpose RAG, multilingual text, and cases where recall (not missing relevant documents) matters more than precision.

### Deploying via HuggingFace TEI

Text Embeddings Inference is the correct server for BGE-M3 — it handles hybrid output natively.

```bash
# ~1.1GB VRAM; can co-reside with larger models on the same GPU machine
docker run --gpus all -p 8001:80 \
  ghcr.io/huggingface/text-embeddings-inference:latest \
  --model-id BAAI/bge-m3 \
  --pooling mean
```

### Milvus Collection Schema

```python
from pymilvus import Collection, CollectionSchema, FieldSchema, DataType

schema = CollectionSchema(fields=[
    FieldSchema("id",            DataType.INT64,              is_primary=True, auto_id=True),
    FieldSchema("text",          DataType.VARCHAR,            max_length=4096),
    FieldSchema("dense_vector",  DataType.FLOAT_VECTOR,       dim=1024),
    FieldSchema("sparse_vector", DataType.SPARSE_FLOAT_VECTOR),
    FieldSchema("metadata",      DataType.JSON),
])

collection = Collection("reviews", schema)

collection.create_index(
    "dense_vector",
    {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}},
)
collection.create_index(
    "sparse_vector",
    {"index_type": "SPARSE_INVERTED_INDEX", "metric_type": "IP"},
)
```

### Hybrid Search Query

```python
from pymilvus import AnnSearchRequest, RRFRanker

dense_req = AnnSearchRequest(
    data=[dense_vector],
    anns_field="dense_vector",
    param={"metric_type": "COSINE", "params": {"ef": 100}},
    limit=20,
)
sparse_req = AnnSearchRequest(
    data=[sparse_vector],
    anns_field="sparse_vector",
    param={"metric_type": "IP"},
    limit=20,
)

results = collection.hybrid_search(
    reqs=[dense_req, sparse_req],
    rerank=RRFRanker(k=60),  # Reciprocal Rank Fusion
    limit=5,
    output_fields=["text", "metadata"],
)
```

**Critical rule**: Never mix vectors from different embedding models in the same Milvus collection. Each model produces an incomparable embedding space — BGE-M3 and Qwen3 vectors cannot be ranked against each other.

---

## PageIndex: Vectorless PDF Retrieval

PageIndex (VectifyAI) takes a structurally different approach: instead of chunking documents and embedding them, it builds a **hierarchical Table-of-Contents index** and uses an LLM to navigate the tree to the right pages.

### Why Vector RAG Fails on Structured PDFs

Three structural problems make standard RAG unreliable on long structured documents:

1. **Chunking destroys context** — a 500-token chunk from page 47 of a 200-page annual report loses all surrounding hierarchy
2. **Semantic drift on financial tables** — "what is the net income for FY2024?" may not embed close to a table where the answer lives as formatted numbers
3. **Table blindness** — dense retrieval struggles with tabular data that is not well-described in prose

### How PageIndex Solves This

1. **Preserves page structure** — each page is a leaf in the TOC tree; section headers are internal nodes
2. **LLM tree navigation** — the LLM traverses section headers to identify relevant pages without ever seeing the full document
3. **No chunking** — full pages are passed to the final generation step, preserving table context and cross-page references

### Accuracy Benchmark

On FinanceBench (financial document Q&A):
- Standard RAG: 45–65% accuracy
- PageIndex: **98.7% accuracy**

This is a 1.5–2x improvement, not a marginal gain.

### Ingestion: Preserve Structure

PageIndex requires page structure to be intact. Do not strip headers, footers, page numbers, or section markers during preprocessing.

```python
from pageindex import PageIndexClient

client = PageIndexClient(api_key=os.environ["PAGEINDEX_API_KEY"])

with open("annual_report_2024.pdf", "rb") as f:
    index = await client.index_document(
        file=f,
        document_id="annual_report_2024",
        preserve_structure=True,  # Critical — keeps the TOC hierarchy intact
        extract_tables=True,       # PageIndex handles tabular extraction
    )
```

### Querying

```python
result = await client.query(
    document_id="annual_report_2024",
    question="What was total operating expense for fiscal year 2024?",
    max_pages=3,              # Pages to retrieve and pass to the LLM
    navigate_to_answer=True,  # LLM navigates the TOC tree
)

# result.pages       — list of full page text with context
# result.source_spans — exact page numbers and line ranges (for citations)
# result.answer      — generated answer with page citations
```

---

## Two-Stage Hybrid: Vector Shortlist → PageIndex Deep-Dive

For corpora containing both short documents and long structured PDFs:

```
Query
 │
 ├── Stage 1: BGE-M3 Milvus hybrid search → top-20 candidates
 │     (fast broad recall across the entire corpus)
 │
 └── Stage 2: For each candidate flagged as a structured PDF:
       → PageIndex query for precise answer extraction
         (slower but precise; only runs on shortlisted candidates)
```

### Implementation (Rust)

```rust
pub async fn hybrid_retrieve(
    query: &str,
    vector_store: &MilvusCollection,
    page_index: &PageIndexClient,
    embedder: &dyn EmbeddingProvider,
) -> Result<Vec<RetrievedChunk>> {
    // Stage 1: broad recall
    let query_vec = embedder.embed(vec![query.to_string()]).await?;
    let candidates = vector_store.search(&query_vec[0], 20).await?;

    // Stage 2: deep-dive on PDF candidates with TOC
    let mut results = Vec::new();
    for candidate in candidates {
        if candidate.metadata.doc_type == DocType::Pdf && candidate.metadata.has_toc {
            let page_result = page_index
                .query(&candidate.metadata.document_id, query)
                .await?;
            results.push(RetrievedChunk::from_page_index(page_result));
        } else {
            results.push(candidate);
        }
    }

    Ok(results)
}
```

---

## Qwen3-Embedding-8B: Precision Retrieval

Qwen3-Embedding-8B (Qwen/Qwen3-Embedding-8B, Apache 2.0) is the highest-ranked general-purpose embedding model on MTEB:

- **English MTEB**: 75.22 (vs BGE-M3: 68.09)
- **Multilingual MTEB**: 70.58
- **Context window**: 32,768 tokens
- **VRAM**: 16–20GB (FP8 quantized)
- **Matryoshka**: Supports lossless dimension reduction: 4096 → 1024 → 256

Use Qwen3 when precision matters more than infrastructure cost: fine-grained semantic matching, media asset selection, high-quality content deduplication. BGE-M3 remains the right choice for general RAG where VRAM and cost are constraints.

### Deploying via vLLM

```bash
# Add to the existing vLLM instance — no new infrastructure required
vllm serve Qwen/Qwen3-Embedding-8B \
  --served-model-name qwen3-embedding \
  --task embed \
  --hf-overrides '{"is_matryoshka": true}' \
  --max-model-len 32768
```

On an H100 80GB running Llama 3.3 70B alongside, reduce `--gpu-memory-utilization` from 0.92 to ~0.85 to leave headroom for Qwen3 (FP8 requires ~8–10GB).

### Calling via OpenAI-Compatible API

```python
import openai

client = openai.AsyncOpenAI(
    base_url="http://localhost:8000/v1",
    api_key="unused",
)

response = await client.embeddings.create(
    model="qwen3-embedding",
    input=["hero image of a restaurant with warm evening lighting"],
    dimensions=1024,          # Matryoshka: 4096 → 1024
    encoding_format="float",
)

embedding = response.data[0].embedding  # List[float], length 1024
```

### Milvus Collection Schema

```python
schema = CollectionSchema(fields=[
    FieldSchema("id",           DataType.INT64,        is_primary=True, auto_id=True),
    FieldSchema("asset_id",     DataType.VARCHAR,      max_length=128),
    FieldSchema("description",  DataType.VARCHAR,      max_length=2048),
    FieldSchema("dense_vector", DataType.FLOAT_VECTOR, dim=1024),  # Matryoshka 1024
    FieldSchema("metadata",     DataType.JSON),
])

collection = Collection("media_assets", schema)
collection.create_index(
    "dense_vector",
    {"index_type": "HNSW", "metric_type": "COSINE", "params": {"M": 16, "efConstruction": 200}},
)
```

The `media_assets` collection is entirely separate from `reviews`. Never query across collections that use different embedding models.

---

## Retrieval Policy / Router Layer

A retrieval policy decides which strategy to apply for each query at runtime. Build this as an explicit, testable function — not logic scattered through handlers.

```rust
// src/services/retrieval/policy.rs

#[derive(Debug, Clone, PartialEq)]
pub enum RetrievalStrategy {
    VectorOnly,    // BGE-M3 hybrid search — general purpose
    PageIndexOnly, // VectifyAI tree-search — structured PDFs
    Hybrid,        // Vector shortlist → PageIndex deep-dive
    Precision,     // Qwen3 dense — high-precision matching
}

pub struct RetrievalRequest {
    pub source_type:          SourceType,
    pub document_page_count:  usize,
    pub has_table_of_contents: bool,
    pub corpus_contains_pdfs: bool,
    pub collection:           Collection,
    pub query_type:           QueryType,
}

pub fn select_strategy(req: &RetrievalRequest) -> RetrievalStrategy {
    // Long structured PDFs with TOC → pure PageIndex
    if req.source_type == SourceType::Pdf
        && req.document_page_count > 20
        && req.has_table_of_contents
    {
        return RetrievalStrategy::PageIndexOnly;
    }

    // Mixed corpus where some docs are large PDFs → two-stage hybrid
    if req.corpus_contains_pdfs && req.query_type != QueryType::Fuzzy {
        return RetrievalStrategy::Hybrid;
    }

    // Media/asset queries need precision
    if req.collection == Collection::MediaAssets {
        return RetrievalStrategy::Precision;
    }

    // Default: BGE-M3 hybrid for general retrieval
    RetrievalStrategy::VectorOnly
}
```

### Router Heuristics Reference

| Document Signal | Strategy |
|----------------|----------|
| PDF + page count > 20 + has_toc | PageIndex |
| Short document (< 2000 chars) | Vector only |
| Mixed corpus with PDFs present | Hybrid |
| Media/asset semantic query | Qwen3 Precision |
| Multilingual or general text | BGE-M3 Vector |
| Real-time, latency < 100ms | BGE-M3 dense-only (skip sparse) |

---

## EmbeddingProvider Abstraction (Rust)

Implement a provider-swap trait so embedding models can change without modifying callers. The same pattern applies regardless of which models you use.

```rust
// src/services/embedding/provider.rs
use async_trait::async_trait;

pub type SparseVector = Vec<(u32, f32)>; // (token_id, weight)

#[async_trait]
pub trait EmbeddingProvider: Send + Sync {
    /// Dense embeddings for all providers
    async fn embed(&self, input: Vec<String>) -> Result<Vec<Vec<f32>>>;

    /// Sparse embeddings — only BGE-M3 produces these
    async fn embed_sparse(&self, input: Vec<String>) -> Result<Vec<SparseVector>>;

    fn dimensions(&self) -> usize;
    fn model_name(&self) -> &str;
}

/// BGE-M3 via HuggingFace TEI on :8001
pub struct BgeM3Provider {
    client: reqwest::Client,
    base_url: String,
}

#[async_trait]
impl EmbeddingProvider for BgeM3Provider {
    async fn embed(&self, input: Vec<String>) -> Result<Vec<Vec<f32>>> {
        self.client
            .post(format!("{}/embed", self.base_url))
            .json(&serde_json::json!({ "inputs": input }))
            .send().await?
            .json::<Vec<Vec<f32>>>().await
            .map_err(Into::into)
    }

    async fn embed_sparse(&self, input: Vec<String>) -> Result<Vec<SparseVector>> {
        self.client
            .post(format!("{}/embed_sparse", self.base_url))
            .json(&serde_json::json!({ "inputs": input }))
            .send().await?
            .json::<Vec<SparseVector>>().await
            .map_err(Into::into)
    }

    fn dimensions(&self) -> usize { 1024 }
    fn model_name(&self) -> &str { "BAAI/bge-m3" }
}

/// Qwen3-Embedding-8B via vLLM on :8000
pub struct Qwen3EmbeddingProvider {
    client: async_openai::Client<async_openai::config::OpenAIConfig>,
}

#[async_trait]
impl EmbeddingProvider for Qwen3EmbeddingProvider {
    async fn embed(&self, input: Vec<String>) -> Result<Vec<Vec<f32>>> {
        use async_openai::types::CreateEmbeddingRequestArgs;
        let req = CreateEmbeddingRequestArgs::default()
            .model("qwen3-embedding")
            .input(input)
            .dimensions(1024u32) // Matryoshka compression
            .build()?;
        let resp = self.client.embeddings().create(req).await?;
        Ok(resp.data.into_iter().map(|e| e.embedding).collect())
    }

    async fn embed_sparse(&self, _input: Vec<String>) -> Result<Vec<SparseVector>> {
        Err(anyhow::anyhow!("Qwen3 produces dense vectors only"))
    }

    fn dimensions(&self) -> usize { 1024 }
    fn model_name(&self) -> &str { "Qwen/Qwen3-Embedding-8B" }
}
```

### Re-indexing on Model Graduation

When upgrading a collection from one embedding model to another, a full re-embed of all documents is required — embedding spaces are model-specific and cannot be migrated in place.

```rust
// src/services/embedding/reindex.rs
pub async fn reindex_collection(
    collection: &MilvusCollection,
    provider: Arc<dyn EmbeddingProvider>,
    batch_size: usize,
) -> Result<ReindexReport> {
    let mut cursor = collection.scan_cursor();
    let mut processed = 0;
    let mut failed = 0;

    while let Some(batch) = cursor.next_batch(batch_size).await? {
        let texts: Vec<String> = batch.iter().map(|r| r.text.clone()).collect();

        match provider.embed(texts).await {
            Ok(embeddings) => {
                collection.upsert_vectors(&batch, &embeddings).await?;
                processed += batch.len();
            }
            Err(e) => {
                tracing::warn!(error = %e, "Batch embedding failed, skipping");
                failed += batch.len();
            }
        }
    }

    Ok(ReindexReport { processed, failed })
}
```

Scaffold this task before it's urgently needed. A full re-index is a planned operation, not a fire drill.

---

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| Mixing vectors from different models in one collection | Completely wrong retrieval rankings | Separate Milvus collection per embedding model |
| Chunking PDFs before PageIndex ingestion | Loses TOC hierarchy; accuracy plummets | Feed full pages with structure preserved |
| Using BGE-M3 for media asset matching | Lower precision than the task requires | Use Qwen3 for precision-sensitive tasks |
| Using Qwen3 for all tasks | 10x VRAM cost for marginal gains on general RAG | Match model to task requirements |
| No retrieval policy layer | Strategy hard-coded in handlers, impossible to A/B test | Build the router as an explicit testable function |
| Not storing source spans | Citations become impossible to generate | Always persist document_id + page_number + char_offset |
| PageIndex on unstructured PDFs | No TOC to navigate; LLM struggles | Fall back to vector RAG for unstructured PDFs |
| Skipping two-stage hybrid for mixed corpora | Either low precision (vector-only) or high cost (PageIndex-everything) | Use vector shortlist to filter, then PageIndex for PDF candidates |
