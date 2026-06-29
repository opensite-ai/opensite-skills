# Worked Example — Rust multi-dependency upgrade (reqwest + ort + sqlx)

A realistic batch upgrade of a Rust application that makes heavy use of SQL.
This walks the six-phase process end to end. Versions are illustrative — always
read the real changelogs for the actual versions in your project.

> **Request:**
> - bump `reqwest` 0.13.2 → 0.13.4 (straightforward)
> - bump `ort` 2.0.0-rc.10 → 2.0.0-rc.12 (may have breaking changes)
> - bump `sqlx` 0.8.6 → 0.9.0 (most critical; breaking changes likely, plus new functionality we may adopt)
>
> Goals: install the upgraded versions, fix any breaking changes across the app.

---

## Phase 0 — Detect ecosystem & baseline
- Ecosystem: Cargo. Manifest `Cargo.toml`, lockfile `Cargo.lock`.
- From-versions read **from `Cargo.lock`** (not the `^` ranges in `Cargo.toml`):
  `reqwest 0.13.2`, `ort 2.0.0-rc.10`, `sqlx 0.8.6`.
- Baseline gate: `cargo build && cargo clippy -- -D warnings && cargo test` → **green**. Recorded.
- Plan drafted from `templates/upgrade-plan.md`.

## Phase 1 — Resolve the graph (conflicts first)
- `cargo update --dry-run` for all three together to preview the resolved graph.
- Peer/feature check: confirm `sqlx` 0.9 is compatible with the runtime (`tokio`) and TLS backend features already enabled; confirm `reqwest` 0.13.4 does not force a different `hyper`/`rustls` major than the rest of the tree.
- Transitive watch: note whether `sqlx` 0.9 pulls a new major of any shared crate (e.g. a `rustls` or `hashbrown` bump) — if so, add it to the Phase 2 changelog list.
- No blocking conflict found. Sequence: `reqwest` (safe) → `ort` → `sqlx` (most invasive last so its build errors aren't masked).

## Phase 2 — Diff the changelogs (search-driven)
Use the search tool; do not rely on memory for these APIs.

- **reqwest 0.13.2 → 0.13.4** — read release notes for 0.13.3 and 0.13.4. Patch-level; expect bug fixes only. Risk: **patch**. Still scan for any behavioral change to default timeouts/redirects. None affecting this app.
- **ort 2.0.0-rc.10 → rc.11 → rc.12** — read the release notes for *both* intermediate RCs (rc.11 changes are easy to miss). ONNX Runtime release-candidate APIs churn: watch for renamed `Session`/`Environment` builders, changed `Value`/tensor extraction signatures, and changed execution-provider registration. Extract each into `templates/changelog-diff.md`. Risk: **minor-but-volatile (RC)**.
- **sqlx 0.8.6 → 0.9.0** — semver-minor in number but **treated as major** for a pre-1.0 crate. Read the 0.9.0 release notes / migration section specifically for "Breaking". Typical 0.9 concerns to confirm against the real notes: changes to `query!`/`query_as!` macro behavior and the offline `.sqlx` data format (may require regenerating with `cargo sqlx prepare`), `Encode`/`Decode`/`Type` trait signature changes, pool/driver API adjustments, and any changed default for a feature flag. Also list **new functionality** the user said they might adopt — but do not adopt yet. Risk: **major**.

## Phase 3 — Install
- Edit `Cargo.toml` ranges to the targets.
- `cargo update -p reqwest --precise 0.13.4`, `-p ort --precise 2.0.0-rc.12`, `-p sqlx --precise 0.9.0` (or a plain `cargo update` constrained by the edited ranges).
- Confirm `Cargo.lock` now pins all three at the intended versions. If `sqlx` resolved lower, a feature/peer constraint is blocking → back to Phase 1.

## Phase 4 — Apply code changes (from Phase 2 notes)
- `reqwest`: no call-site changes expected; confirm by build.
- `ort`: grep for the renamed session/value symbols from the changelog-diff; update each call site to the documented rc.12 API. Build, read first error, fix, repeat — do not batch-guess.
- `sqlx`: grep every `query!`, `query_as!`, `sqlx::query`, custom `impl Type/Encode/Decode`, and pool-construction site. Apply the documented 0.9 changes. If the offline macro format changed, run `cargo sqlx prepare` to regenerate `.sqlx`. For any **behavioral** change (e.g. a default that affects query results), audit call sites and add a test.
- If a build error doesn't map to a Phase 2 note → return to Phase 2 and search for that exact symbol. Don't improvise.
- Keep the diff minimal. The user's "new functionality we can use" for sqlx is a **separate, explicit follow-up** unless they confirmed adopting it now.

## Phase 5 — Verify & report
- `cargo build && cargo clippy -- -D warnings && cargo test` → require green.
- Verify any behavioral-change paths (sqlx defaults) are exercised by tests; add coverage if missing.
- Report (becomes the PR body):
  - `reqwest 0.13.2 → 0.13.4` — patch, no code changes.
  - `ort 2.0.0-rc.10 → 2.0.0-rc.12` — updated N call sites for the renamed session/value API.
  - `sqlx 0.8.6 → 0.9.0` — regenerated offline data, updated M query/Type sites; behavioral caveat: `<the changed default>` — callers should be aware. New functionality available but **not adopted** (deferred per scope).
