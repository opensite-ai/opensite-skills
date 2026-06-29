# Activation Guide

## Best-Fit Tasks
- Upgrading one or more dependencies — a single patch bump, a batch of mixed bumps, or a semver-major migration — in any ecosystem (Cargo, npm/pnpm/yarn, pip/Poetry/uv, Go modules, Maven/Gradle, Bundler, Composer).
- Resolving version or peer-dependency conflicts before installing.
- Finding and applying the code changes required by a dependency's breaking changes, sourced from its changelog or migration guide.
- Best trigger phrase: "bump X from a.b.c to x.y.z and fix any breaking changes", "upgrade these libraries", "migrate to vN of <package>".

## Explicit Invocation
- `Use $dependency-upgrade-orchestrator to bump reqwest, ort, and sqlx to their target versions, resolve any conflicts, read the changelogs for breaking changes, apply the code fixes, and verify with cargo build, clippy, and test.`

## When NOT to Use
- A from-scratch dependency *addition* with no existing version to diff against — that is a normal install, not an upgrade.
- A change that touches 50+ files: pair with `large-scale-refactor`, which supplies the scope-gate and file-budget guardrails. This skill decides *what* changes; `large-scale-refactor` governs *how* a large change is executed.

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need: the upgrade-plan and changelog-diff templates, and the worked examples.
- The process is ecosystem-agnostic; the command map in SKILL.md § 9 translates each phase to the project's package manager. Always defer to the repo's own canonical build/lint/test commands when they exist.
- The standard metadata and this guide are portable across skills-compatible agents; any Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
