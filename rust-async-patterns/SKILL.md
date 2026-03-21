---
name: rust-async-patterns
description: >
  Senior-level async Rust patterns: Future Send bound failures, Rust 2024
  lifetime capture rules, task cancellation with CancellationToken,
  blocking/async boundary design, and timeout composition. Use when debugging
  async compilation errors, structuring long-lived tasks, or designing services
  that mix async and CPU-bound work.
compatibility: >
  Requires a Rust async codebase and cargo; reproduction of compiler errors
  helps for targeted fixes.
metadata:
  opensite-category: backend
  opensite-scope: shared
  opensite-visibility: public
---
# Rust Async Patterns

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.

Async Rust is not simply "add `.await`." The ownership model, `Send` bounds, and lifetime capture rules surface unique errors that are easy to misdiagnose. This skill covers the non-obvious patterns that senior Rust engineers reach for daily.

---

## Future `Send` Bound Failures

The most common async compilation error in multi-threaded runtimes:

```
error[E0277]: `*mut ()` cannot be sent between threads safely
   --> src/handlers/process.rs:42:5
    |
    | future returned by `process_request` is not `Send`
```

### Why It Happens

Tokio's `spawn` requires futures to be `Send`. A future is only `Send` if every value it holds across `.await` points is `Send`. Non-`Send` types like `Rc<T>`, `*mut T`, `RefCell<T>`, and most `MutexGuard` (depending on implementation) break this.

```rust
// ❌ Rc is not Send — the future holds Rc across an await point
async fn process() {
    let data = Rc::new(vec![1, 2, 3]); // Rc<Vec<i32>> is !Send
    do_io().await;
    println!("{:?}", data); // 'data' still live here — future is !Send
}

// ✅ Use Arc instead
async fn process() {
    let data = Arc::new(vec![1, 2, 3]);
    do_io().await;
    println!("{:?}", data);
}
```

### MutexGuard Across Await Points

```rust
use tokio::sync::Mutex; // NOT std::sync::Mutex

// ❌ std::sync::MutexGuard is !Send
async fn update(state: Arc<std::sync::Mutex<State>>) {
    let guard = state.lock().unwrap();
    do_io().await; // guard held across await — !Send
    guard.field = 42;
}

// ✅ Drop the guard before awaiting
async fn update(state: Arc<std::sync::Mutex<State>>) {
    {
        let mut guard = state.lock().unwrap();
        guard.field = 42;
    } // guard dropped here
    do_io().await;
}

// ✅ Or use tokio::sync::Mutex which produces a Send guard
async fn update(state: Arc<tokio::sync::Mutex<State>>) {
    let mut guard = state.lock().await;
    guard.field = 42;
    do_io().await; // tokio MutexGuard is Send
}
```

### Diagnosing `Send` Failures

The compiler error usually points to the spawn site, not the source of the problem. Add a temporary bound assertion to get a better span:

```rust
fn assert_send<T: Send>(_: T) {}

// Add this call right before the spawn to get a cleaner error
assert_send(process_request(req));
tokio::spawn(process_request(req));
```

---

## Rust 2024: Lifetime Capture in `async fn`

Rust 2024 (edition = "2024" in Cargo.toml) changes how lifetimes are captured in `async fn` return types. This breaks code that worked in edition 2021.

### The Problem

In edition 2021, `async fn` only captured lifetime parameters that appeared in the return type. In edition 2024, **all lifetime parameters are captured** by default.

```rust
// Compiles in edition 2021, fails in edition 2024
async fn process<'a>(data: &'a str) -> String {
    // 'a is captured even though String doesn't borrow from data
    do_something(data).await
}

// Caller can no longer hold a shorter-lived reference:
let result = {
    let s = String::from("hello");
    process(&s) // error: s doesn't live long enough
};
result.await;
```

### The Fix: `use<>` Syntax (Rust 1.82+)

```rust
// Explicitly list which lifetimes the future captures
async fn process<'a>(data: &'a str) -> impl Future<Output = String> + use<'a> {
    do_something(data).await
}

// Or use the precise captures syntax on the return type
fn process<'a>(data: &'a str) -> impl Future<Output = String> + use<'a> {
    async move { do_something(data).await }
}
```

### When You Hit This in Axum Handlers

Axum state extractors use lifetime bounds. If you see "the associated type `Future` must implement `Send`" in an Axum handler after upgrading to edition 2024:

```rust
// ❌ Implicitly captures the request lifetime in edition 2024
async fn handler(State(db): State<DbPool>, body: String) -> impl IntoResponse {
    db.query(&body).await // body lifetime captured unnecessarily
}

// ✅ Avoid holding references across await when possible
async fn handler(State(db): State<DbPool>, body: String) -> impl IntoResponse {
    let query = body.clone(); // owned value, no lifetime issue
    db.query(&query).await
}
```

---

## Task Cancellation with `CancellationToken`

Tokio tasks don't have a built-in cancellation mechanism. The idiomatic pattern uses `tokio_util::sync::CancellationToken`.

```rust
use tokio_util::sync::CancellationToken;
use tokio::time::{sleep, Duration};

async fn long_running_task(cancel: CancellationToken) {
    loop {
        tokio::select! {
            _ = cancel.cancelled() => {
                tracing::info!("Task received cancellation signal, shutting down");
                return;
            }
            _ = sleep(Duration::from_secs(1)) => {
                do_work().await;
            }
        }
    }
}

// Spawning with cancellation support
let cancel = CancellationToken::new();
let child_cancel = cancel.child_token(); // child is cancelled when parent is cancelled

let handle = tokio::spawn(long_running_task(child_cancel));

// Later — graceful shutdown
cancel.cancel();
handle.await.expect("task panicked");
```

### Graceful Shutdown Pattern for Axum Services

```rust
use tokio::signal;

async fn run_server(app: Router, cancel: CancellationToken) {
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();

    axum::serve(listener, app)
        .with_graceful_shutdown(async move {
            cancel.cancelled().await;
        })
        .await
        .unwrap();
}

#[tokio::main]
async fn main() {
    let cancel = CancellationToken::new();

    // Spawn CTRL+C handler
    let cancel_clone = cancel.clone();
    tokio::spawn(async move {
        signal::ctrl_c().await.expect("failed to install CTRL+C handler");
        tracing::info!("Received shutdown signal");
        cancel_clone.cancel();
    });

    run_server(build_app(), cancel).await;
}
```

---

## Blocking/Async Boundary Design

Calling blocking code from async context starves the Tokio executor. Tokio's worker threads are meant for async work — a blocking call on a worker thread blocks every other future scheduled on that thread.

### The Rule

Any operation that may take longer than ~100µs without yielding to the executor should be dispatched to `spawn_blocking`:

- File I/O (unless using `tokio::fs`)
- CPU-heavy computation (image processing, encryption, compression)
- Synchronous database drivers
- Any third-party library with blocking APIs

```rust
// ❌ Blocks the executor thread
async fn generate_thumbnail(path: &Path) -> Result<Vec<u8>> {
    let image = image::open(path)?; // blocking read + decode
    let thumbnail = image.thumbnail(200, 200);
    let mut buf = Vec::new();
    thumbnail.write_to(&mut Cursor::new(&mut buf), ImageFormat::Jpeg)?;
    Ok(buf)
}

// ✅ Offload to blocking thread pool
async fn generate_thumbnail(path: PathBuf) -> Result<Vec<u8>> {
    tokio::task::spawn_blocking(move || {
        let image = image::open(&path)?;
        let thumbnail = image.thumbnail(200, 200);
        let mut buf = Vec::new();
        thumbnail.write_to(&mut Cursor::new(&mut buf), ImageFormat::Jpeg)?;
        Ok(buf)
    })
    .await
    .map_err(|e| anyhow::anyhow!("blocking task panicked: {e}"))??
}
```

### `spawn_blocking` Ownership Rules

`spawn_blocking` requires `'static` closures. Everything captured must be owned, not borrowed:

```rust
// ❌ Borrows 'data' — not 'static
async fn process(data: &[u8]) -> Result<String> {
    tokio::task::spawn_blocking(|| {
        cpu_intensive(data) // captures &[u8], not 'static
    }).await??
}

// ✅ Clone or use Arc to make it owned
async fn process(data: Vec<u8>) -> Result<String> {
    tokio::task::spawn_blocking(move || {
        cpu_intensive(&data)
    }).await??
}
```

---

## Timeout Composition

Never rely on infrastructure-level timeouts alone. Apply timeouts at the call site with explicit error context.

```rust
use tokio::time::{timeout, Duration};

// Single operation timeout
async fn fetch_with_timeout(url: &str) -> Result<String> {
    timeout(Duration::from_secs(10), fetch(url))
        .await
        .map_err(|_| anyhow::anyhow!("fetch timed out after 10s: {url}"))?
}

// Timeout across multiple concurrent operations
async fn gather_data(ids: Vec<u64>) -> Result<Vec<Data>> {
    let futures = ids.iter().map(|id| fetch_data(*id));
    let results = timeout(
        Duration::from_secs(30),
        futures::future::join_all(futures),
    )
    .await
    .map_err(|_| anyhow::anyhow!("data gathering timed out after 30s"))?;

    results.into_iter().collect()
}
```

### Layered Timeouts with `select!`

For operations with distinct deadline requirements:

```rust
async fn process_with_deadlines(req: Request) -> Result<Response> {
    let db_deadline = Duration::from_millis(500);
    let total_deadline = Duration::from_secs(5);

    tokio::select! {
        _ = sleep(total_deadline) => {
            Err(anyhow::anyhow!("total request timeout exceeded"))
        }
        result = async {
            let data = timeout(db_deadline, db_query(&req))
                .await
                .map_err(|_| anyhow::anyhow!("db query timed out"))??;
            build_response(data).await
        } => result,
    }
}
```

---

## Structured Concurrency with `JoinSet`

`tokio::task::JoinSet` manages a set of spawned tasks and propagates the first failure:

```rust
use tokio::task::JoinSet;

async fn process_all(items: Vec<Item>) -> Result<Vec<Output>> {
    let mut set = JoinSet::new();

    for item in items {
        set.spawn(async move { process_item(item).await });
    }

    let mut results = Vec::new();
    while let Some(result) = set.join_next().await {
        match result {
            Ok(Ok(output)) => results.push(output),
            Ok(Err(e)) => {
                set.abort_all(); // Cancel remaining tasks on first error
                return Err(e);
            }
            Err(e) => {
                set.abort_all();
                return Err(anyhow::anyhow!("task panicked: {e}"));
            }
        }
    }

    Ok(results)
}
```

---

## Common Async Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Non-`Send` type across `.await` | Compile error: future is not `Send` | Scope the non-Send value; use `Arc` over `Rc`; drop guards before awaiting |
| `std::sync::MutexGuard` across `.await` | `!Send` compile error | Use `tokio::sync::Mutex` or drop the guard before the await |
| Blocking call on async thread | Executor starvation, high latency under load | `tokio::task::spawn_blocking` for anything > ~100µs |
| Missing `move` in `spawn` closure | Lifetime/borrow error | Use `move` closures; own all captured data |
| Infinite retry without backoff | Hot loop starves executor | `tokio::time::sleep` with exponential backoff |
| Ignoring `JoinHandle` | Task failure silently discarded | Always `.await` handles or use `JoinSet` |
| `unwrap()` in async task | Silent panic kills task with no trace | Use `?` with proper error types; never unwrap in handler code |
