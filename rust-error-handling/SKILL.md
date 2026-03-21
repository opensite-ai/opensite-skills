---
name: rust-error-handling
description: >
  Idiomatic Rust error handling design for libraries and applications: thiserror
  vs anyhow boundary decisions, error hierarchy design, context chain
  propagation, HTTP handler error mapping, and the common patterns that prevent
  error type proliferation. Use when designing error types for a new module,
  deciding between thiserror and anyhow, or debugging opaque error messages in
  production.
compatibility: >
  Requires a Rust codebase and cargo; error-chain validation benefits from local
  test coverage.
metadata:
  opensite-category: backend
  opensite-scope: shared
  opensite-visibility: public
---
# Rust Error Handling

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)

Rust's error handling requires deliberate design decisions that compound across a codebase. The wrong choice at a module boundary forces changes across every caller. This skill covers the architecture decisions, not just the syntax.

---

## The Core Boundary: `thiserror` vs `anyhow`

The single most important decision: **are you writing library code or application code?**

| Concern | Library (`thiserror`) | Application (`anyhow`) |
|---------|----------------------|------------------------|
| Callers programmatically match errors | Yes | No |
| Error types are part of the public API | Yes | No |
| Ergonomics of error propagation | Verbose | Ergonomic (`?` just works) |
| Error context chain | Manual | `context()` / `with_context()` |
| When to use | `src/services/*`, any reusable module | `src/handlers/*`, `main.rs`, scripts |

**The rule**: Use `thiserror` at library and service boundaries. Use `anyhow` at application boundaries (handlers, CLI entry points, scripts). Never use `anyhow` in code that other code will call and need to match on.

---

## Designing Error Hierarchies with `thiserror`

### Single-Layer Enum (Most Common)

```rust
// src/services/embedding/error.rs
use thiserror::Error;

#[derive(Debug, Error)]
pub enum EmbeddingError {
    #[error("embedding provider returned HTTP {status}: {message}")]
    ProviderError {
        status: u16,
        message: String,
    },

    #[error("input too long: {len} tokens, max {max}")]
    InputTooLong { len: usize, max: usize },

    #[error("embedding dimensions mismatch: expected {expected}, got {actual}")]
    DimensionMismatch { expected: usize, actual: usize },

    #[error("network error: {0}")]
    Network(#[from] reqwest::Error),

    #[error("serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
}
```

### Hierarchical Errors for Complex Modules

When a service has subsystems, use nested error enums so callers can match at the right level:

```rust
#[derive(Debug, Error)]
pub enum StorageError {
    #[error("database error: {0}")]
    Database(#[from] DatabaseError),

    #[error("object store error: {0}")]
    ObjectStore(#[from] ObjectStoreError),

    #[error("resource not found: {id}")]
    NotFound { id: String },
}

#[derive(Debug, Error)]
pub enum DatabaseError {
    #[error("connection pool exhausted")]
    PoolExhausted,

    #[error("query failed: {0}")]
    Query(#[from] tokio_postgres::Error),

    #[error("migration failed: {0}")]
    Migration(String),
}
```

### `#[from]` vs Manual Conversion

`#[from]` implements `From<SourceError>` for your enum. Use it when the wrapping adds no additional context. Add extra fields when context matters:

```rust
// #[from] when wrapping is sufficient
#[error("HTTP request failed: {0}")]
Request(#[from] reqwest::Error),

// Manual conversion when you need to add context
#[error("failed to fetch model {model_name}: {source}")]
ModelFetch {
    model_name: String,
    #[source] source: reqwest::Error,
},
```

---

## `anyhow` for Application Code

In handlers and top-level application code, `anyhow::Result<T>` (alias for `Result<T, anyhow::Error>`) provides ergonomic propagation with a context chain:

```rust
use anyhow::{Context, Result};

async fn process_request(id: u64) -> Result<Response> {
    let record = db.find(id)
        .await
        .with_context(|| format!("failed to load record {id} from database"))?;

    let embedding = embed(&record.text)
        .await
        .context("embedding generation failed")?;

    store_result(id, embedding)
        .await
        .with_context(|| format!("failed to store embedding for record {id}"))?;

    Ok(Response::success())
}
```

The context chain makes the error message actionable:
```
failed to store embedding for record 42: connection pool exhausted: pool timeout after 30s
```

Each `.context()` call wraps the prior error, building a readable chain from innermost (root cause) to outermost (what the user was trying to do).

---

## `AppError`: Mapping Errors to HTTP Responses

In Axum applications, define a central `AppError` type that implements `IntoResponse`. This is the seam between internal error types and HTTP status codes.

```rust
// src/error.rs
use axum::{http::StatusCode, response::{IntoResponse, Response}, Json};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum AppError {
    #[error("not found: {0}")]
    NotFound(String),

    #[error("bad request: {0}")]
    BadRequest(String),

    #[error("unauthorized")]
    Unauthorized,

    #[error("internal error")]
    Internal(#[from] anyhow::Error),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, message) = match &self {
            AppError::NotFound(msg)   => (StatusCode::NOT_FOUND, msg.clone()),
            AppError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg.clone()),
            AppError::Unauthorized    => (StatusCode::UNAUTHORIZED, "unauthorized".into()),
            AppError::Internal(e) => {
                // Log internal errors with full chain; return generic message to client
                tracing::error!(error = %e, "internal error");
                (StatusCode::INTERNAL_SERVER_ERROR, "internal server error".into())
            }
        };

        (status, Json(serde_json::json!({ "error": message }))).into_response()
    }
}
```

### Handler Usage

```rust
// Handlers return Result<Json<T>, AppError>
// anyhow::Error automatically converts to AppError::Internal via #[from]
pub async fn get_embedding(
    State(state): State<AppState>,
    Path(id): Path<u64>,
) -> Result<Json<EmbeddingResponse>, AppError> {
    let record = state.db
        .find(id)
        .await
        .with_context(|| format!("record {id} not found in database"))
        .map_err(|e| {
            if is_not_found(&e) {
                AppError::NotFound(format!("record {id}"))
            } else {
                AppError::Internal(e)
            }
        })?;

    let response = build_response(record)?;
    Ok(Json(response))
}
```

---

## Converting Between Error Domains

When a service boundary returns a domain-specific error that needs to become an `AppError`:

```rust
// Implement From for the conversion instead of using inline match everywhere
impl From<EmbeddingError> for AppError {
    fn from(e: EmbeddingError) -> Self {
        match e {
            EmbeddingError::InputTooLong { len, max } => {
                AppError::BadRequest(format!("input too long: {len} tokens (max {max})"))
            }
            EmbeddingError::DimensionMismatch { .. } => {
                AppError::Internal(anyhow::anyhow!("{e}"))
            }
            other => AppError::Internal(anyhow::anyhow!("{other}")),
        }
    }
}

// Now ? works cleanly in handlers
pub async fn embed_handler(/* ... */) -> Result<Json<Response>, AppError> {
    let embedding = embedding_service.embed(input).await?; // EmbeddingError → AppError
    Ok(Json(embedding.into()))
}
```

---

## Error Context Chain Best Practices

### What Makes a Good Context String

```rust
// ❌ Context that doesn't help debug
.context("failed")?

// ❌ Context that duplicates the inner error message
.context("reqwest error")?  // reqwest::Error already says it's a reqwest error

// ✅ Context that answers "what were we trying to do?"
.with_context(|| format!("fetch model weights for model {model_id} from S3"))?

// ✅ Context that includes the relevant identifier
.with_context(|| format!("update embedding for resource {resource_type}/{resource_id}"))?
```

### Log vs. Return: Choosing Where to Handle

```rust
// ❌ Log AND return — the error gets reported twice
async fn process() -> Result<()> {
    let result = do_work().await.map_err(|e| {
        tracing::error!("failed: {e}");  // logged here
        e
    })?;
    // ...
    Ok(())
}

// ✅ Return the error with context; let the caller (handler) decide to log
async fn process() -> Result<()> {
    do_work()
        .await
        .context("processing failed")?;
    Ok(())
}

// ✅ In the handler — one place to log, then convert to HTTP response
pub async fn handler(/* ... */) -> Result<Json<Response>, AppError> {
    process().await.map_err(|e| {
        tracing::error!(error = %e, "request processing failed");
        AppError::Internal(e)
    })?;
    Ok(Json(Response::ok()))
}
```

---

## Avoiding Common Error Design Mistakes

### Don't Box `dyn Error` in Library Code

```rust
// ❌ Opaque — callers cannot match on variants
pub fn parse(input: &str) -> Result<Config, Box<dyn std::error::Error>> { ... }

// ✅ Named enum — callers can match
pub fn parse(input: &str) -> Result<Config, ConfigError> { ... }
```

### Don't Overuse `unwrap` / `expect`

```rust
// ❌ Panics in production, no context
let value = map.get("key").unwrap();

// ✅ Propagate with context
let value = map.get("key")
    .ok_or_else(|| anyhow::anyhow!("required key 'key' missing from config map"))?;

// ✅ Use expect only for things that are truly invariants, with a message
// that explains the invariant (not just "should be Some")
let socket = listener.accept().expect(
    "TcpListener::accept should only fail if the socket is already closed, which cannot happen here"
);
```

### Don't Mix `thiserror` Enums into `anyhow` Chains Unnecessarily

```rust
// ❌ Wraps a typed error into anyhow before propagation, losing matchability
let result = service.call().await
    .map_err(|e| anyhow::anyhow!("{e}"))?; // EmbeddingError is now opaque

// ✅ Keep the typed error until the application boundary
let result = service.call().await?; // propagate EmbeddingError to the handler
// Handler maps EmbeddingError → AppError with full type visibility
```

---

## Error Type Checklist

When designing a new module's error type:

- [ ] Is this module called by other modules? → `thiserror` enum with named variants
- [ ] Is this a handler or entry point? → `anyhow::Result` for ergonomic propagation
- [ ] Are callers expected to match on specific variants? → Named fields, not just `String`
- [ ] Does the error need to become an HTTP response? → Implement `From<YourError> for AppError`
- [ ] Do you have a `String`-carrying catch-all variant? → Consider if it should be `#[source] SomeError` instead
- [ ] Are you using `.context()` on every `?`? → Good. If not, add it — the chain matters in production
