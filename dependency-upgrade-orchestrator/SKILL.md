---
name: dependency-upgrade-orchestrator
description: >
  Language- and framework-agnostic process for upgrading one or more
  dependencies safely and systematically. Resolves version and peer conflicts
  before touching code, uses search tools to read changelogs and migration
  guides to find the exact breaking changes between the installed and target
  versions, applies every required code change, and verifies with the project's
  own build, lint, and test gates. Use when asked to bump, upgrade, or update a
  package (or a batch of packages), migrate a major version, handle breaking
  changes from a dependency, or modernize a lockfile across any ecosystem
  (Cargo, npm/pnpm/yarn, pip/Poetry/uv, Go modules, Maven/Gradle, Bundler,
  Composer, and others).
compatibility: >
  Requires shell access and the project's package manager and toolchain
  (e.g. cargo, npm/pnpm/yarn, pip/poetry/uv, go, maven/gradle, bundler).
  Changelog discovery benefits from a web search tool; breaking-change
  verification benefits from a working build/test command.
metadata:
  opensite-category: ops
  opensite-scope: shared
  opensite-visibility: public
---
# Dependency Upgrade Orchestrator

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Upgrade plan template: [templates/upgrade-plan.md](templates/upgrade-plan.md)
- Per-dependency changelog template: [templates/changelog-diff.md](templates/changelog-diff.md)
- Worked Rust example (reqwest + ort + sqlx): [examples/rust-multi-upgrade.md](examples/rust-multi-upgrade.md)
- Worked JS example (npm major bump): [examples/js-major-upgrade.md](examples/js-major-upgrade.md)

Upgrading a dependency is not "change the number and run install." A version bump can shift a transitive graph, break a peer constraint, change a public API, alter default behavior, or silently change runtime semantics without a compile error. This skill is a disciplined, repeatable process that surfaces those changes **before** they reach production and fixes them deliberately.

The process is identical across ecosystems — only the commands change. Detect the ecosystem first, then map each phase onto that ecosystem's tooling using the table in **§ 9 (Ecosystem Command Map)** below.

---

## Operating Principles

1. **Read before you write.** Never apply a code change for a breaking change you have not confirmed in a changelog, release note, or migration guide. Guessing the shape of a new API wastes a build cycle and introduces subtle bugs.
2. **One source of truth per phase.** Resolve the dependency graph first; only then read changelogs; only then edit code; only then verify. Do not interleave — interleaving is how scope drifts.
3. **Smallest viable diff.** Fix what the upgrade requires. Do not refactor unrelated code, adopt new optional features, or reformat files in the same change unless the user explicitly asked for it (the Rust example below is an exception only because the user asked to adopt new sqlx functionality).
4. **Verify with the project's own gates.** The authority on "did it work" is the project's build, lint, and test commands — not your reading of the diff.
5. **Halt and surface on ambiguity.** If a changelog is missing, a migration path is unclear, or a conflict cannot be resolved without a judgment call, stop and report rather than force a resolution.

---

## The Six-Phase Process

### Phase 0 — Detect Ecosystem and Establish Baseline

1. Identify the package manager and toolchain from the manifest/lockfile present in the repo (`Cargo.toml`/`Cargo.lock`, `package.json`/`pnpm-lock.yaml`/`package-lock.json`/`yarn.lock`, `pyproject.toml`/`poetry.lock`/`requirements.txt`, `go.mod`, `pom.xml`/`build.gradle`, `Gemfile.lock`, `composer.json`). See **§ 9 (Ecosystem Command Map)** below.
2. Record the **currently installed** version of each target dependency from the **lockfile**, not the manifest range. The manifest may say `^1.2` while the lockfile pins `1.2.7`; the lockfile is the real "from" version.
3. Confirm the baseline is green: run the project's build, lint, and test commands and record the result. **Never start an upgrade on a red baseline** — you will not be able to attribute later failures to the upgrade.
4. Write an upgrade plan from [templates/upgrade-plan.md](templates/upgrade-plan.md) listing each dependency, its from-version, target-version, and a placeholder risk rating.

### Phase 1 — Resolve the Dependency Graph (Conflict Check First)

Do this for the **whole set** of requested upgrades together, not one at a time — upgrades can conflict with each other, not just with existing deps.

1. **Dry-run the resolution.** Use the ecosystem's resolver in a non-mutating mode where available (`cargo update --dry-run`, `npm install --dry-run`, `npm-check-updates`, `go get` in a scratch clone, `poetry update --dry-run`, `pip install --dry-run`) to preview what the graph would become.
2. **Check direct + peer constraints.** Confirm each target version is allowed by every other package that depends on it. In JS, peer dependency conflicts are the most common failure — resolve them by also upgrading the constraining package, not by forcing (`--force`/`--legacy-peer-deps`) unless the user accepts the risk.
3. **Check transitive shifts.** Note any transitive dependency that changes a major version as a side effect — these can introduce breaking changes you did not request. Add them to the changelog list in Phase 2.
4. **Sequence the upgrades.** If A must reach version X before B can upgrade, order them. Record the order in the plan.
5. If conflicts cannot be resolved without dropping or downgrading another dependency, **halt and report the conflict** with the constraint chain. Do not silently pin around it.

### Phase 2 — Diff the Changelogs (Search-Driven)

For each target dependency (and any transitive major bump from Phase 1), find the **authoritative** record of what changed between the from-version and the target-version. Use search tools — do not rely on memory; library APIs change faster than any training cutoff.

1. **Locate the primary source**, in priority order:
   - The dependency's `CHANGELOG.md` / release notes on its source repo, read **for every intermediate version** between from and to (a 0.8.0 → 0.9.0 jump may have breaking changes introduced in 0.8.3).
   - A dedicated migration/upgrade guide (common for major bumps: "Migrating to vN", "Upgrade guide").
   - GitHub Releases pages and the compare view (`/compare/v0.8.6...v0.9.0`).
   - For semver-major bumps, expect breaking changes and search specifically for the "Breaking Changes" / "BREAKING" sections.
2. **Use the search tool to fetch and read these pages**, then extract into [templates/changelog-diff.md](templates/changelog-diff.md) per dependency:
   - **Breaking changes** (removed/renamed APIs, changed signatures, changed defaults, changed MSRV/runtime minimums).
   - **Behavioral changes** that compile fine but change runtime results (these are the dangerous ones — note them explicitly).
   - **Deprecations** to be aware of (fix only if they now error).
   - **New functionality** relevant to this codebase — list it, but only adopt it if the user asked.
3. **Classify risk** per dependency: patch (no API change expected) / minor (additive, watch for behavioral changes) / major (assume breaking). Update the plan's risk column. Patch/minor bumps still get a changelog read — "patch" releases occasionally ship behavioral fixes that change results.

### Phase 3 — Install the Upgraded Versions

1. Update the manifest to the target versions (edit the manifest range, then let the resolver update the lockfile — do not hand-edit the lockfile).
2. Run the install/update command so the lockfile reflects the new resolved graph.
3. Confirm the lockfile now pins each target dependency at the intended version. If the resolver picked a lower version than requested, a constraint elsewhere is blocking it — return to Phase 1.

### Phase 4 — Apply Code Changes for Breaking Changes

Work from the changelog-diff notes produced in Phase 2 — this phase is mechanical execution of a known list, not discovery.

1. **Locate every call site.** Grep the codebase for each changed/removed/renamed symbol, changed function signature, and changed import path. Build the complete list of files to touch before editing any of them.
2. **Apply each fix at its call sites**, matching the new API exactly as documented. For behavioral changes with no compile error, audit the call sites and adjust logic or add tests to lock in the intended behavior.
3. **Handle config/feature-flag changes** (renamed Cargo features, changed default features, renamed npm package exports, changed build config).
4. **Iterate against the compiler/build, not against guesses.** Run the build, read the first error, fix it, repeat. Do not batch-guess multiple fixes for errors you have not yet seen.
5. If a build error does not map to anything in your Phase 2 notes, **return to Phase 2** and search for the specific symbol — you missed a changelog entry. Do not invent a fix.
6. Keep the diff scoped (Operating Principle 3). Adopting new functionality is a **separate, explicit** step the user must request.

### Phase 5 — Verify and Report

1. Run the full gate sequence the project uses, in order, and require each to pass: **build → lint → test** (e.g. `cargo build && cargo clippy -- -D warnings && cargo test`; `pnpm build && pnpm lint && pnpm test`).
2. For behavioral changes flagged in Phase 2, verify the relevant tests actually exercise the changed path; add a test if coverage is missing.
3. If any gate fails for a reason tied to the upgrade, return to Phase 4. If it fails for an unrelated flaky reason, note it but do not "fix" it inside the upgrade.
4. **Write the summary**: per dependency, from→to version, the breaking changes handled, the files touched, and any behavioral changes that callers should know about. This summary is the PR body.

---

## When Things Go Wrong

| Situation | Action |
|-----------|--------|
| Peer/version conflict cannot be resolved | Halt. Report the constraint chain (who requires what). Propose the minimal set of additional upgrades that would resolve it; let the user decide. |
| Changelog missing or sparse | Fall back to the GitHub compare view and the diff of the public API surface; if still unclear, note the dependency as "unverified — manual review needed" and surface it. Do not guess at API shape. |
| Build error not in the changelog notes | Return to Phase 2 and search for the specific symbol/error. A missing entry means incomplete changelog reading, not a license to improvise. |
| A transitive major bump appears unexpectedly | Add it to the Phase 2 changelog list and treat it as a first-class upgrade. |
| Behavioral change with no compile error | Highest-risk case. Locate call sites, reason about the new behavior, add/adjust tests to lock it in, and call it out explicitly in the report. |
| Upgrade touches 50+ files | Hand off to `large-scale-refactor` for scope-gate and file-budget guardrails; this skill defines *what* changes, that skill governs *how* a large change is executed safely. |

---

## 9. Ecosystem Command Map

Map each phase onto the project's tooling. This table is a starting point; defer to whatever the repo's scripts (`Makefile`, `package.json` scripts, CI config) define as the canonical commands.

| Phase | Cargo (Rust) | npm / pnpm / yarn (JS) | pip / Poetry / uv (Python) | Go modules | Maven / Gradle (JVM) | Bundler (Ruby) |
|-------|--------------|------------------------|-----------------------------|------------|----------------------|----------------|
| Installed version | `Cargo.lock` | lockfile | `*.lock` / `pip freeze` | `go.mod` / `go.sum` | `mvn dependency:tree` | `Gemfile.lock` |
| Conflict dry-run | `cargo update --dry-run` | `npm install --dry-run` / `ncu` | `pip install --dry-run` / `poetry update --dry-run` | `go get` in scratch clone | `mvn versions:display-dependency-updates` | `bundle update --conservative` |
| Install upgrade | edit `Cargo.toml`; `cargo update -p <dep> --precise <v>` | edit `package.json`; `pnpm up <dep>@<v>` | edit `pyproject.toml`; `poetry add <dep>@<v>` | `go get <dep>@<v>` | edit POM/Gradle | edit `Gemfile`; `bundle update <dep>` |
| Find call sites | `grep` / `rg` | `grep` / `rg` | `grep` / `rg` | `grep` / `rg` | `grep` / `rg` | `grep` / `rg` |
| Build gate | `cargo build` | `pnpm build` / `tsc` | `python -m build` / import check | `go build ./...` | `mvn compile` / `gradle build` | `bundle exec rake` |
| Lint gate | `cargo clippy -- -D warnings` | `pnpm lint` | `ruff` / `flake8` / `mypy` | `go vet ./...` | checkstyle/spotbugs | `rubocop` |
| Test gate | `cargo test` | `pnpm test` | `pytest` | `go test ./...` | `mvn test` / `gradle test` | `bundle exec rspec` |

---

## Quick Checklist

- [ ] Ecosystem detected; baseline build/lint/test is **green** before starting
- [ ] From-versions read from the **lockfile**, not the manifest range
- [ ] Whole upgrade set resolved together; peer/transitive conflicts checked and sequenced
- [ ] Changelogs/migration guides read via search for **every intermediate version**, breaking + behavioral changes extracted
- [ ] Manifest edited and lockfile regenerated; target versions confirmed pinned
- [ ] Every changed/removed symbol grepped; all call sites updated to the documented new API
- [ ] Behavioral (non-compile-error) changes audited and covered by tests
- [ ] Build → lint → test all green
- [ ] Report written: per-dep from→to, breaking changes handled, files touched, behavioral caveats
