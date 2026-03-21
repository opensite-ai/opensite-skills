# Activation Guide

## Best-Fit Tasks
- Production-grade Sidekiq job design covering idempotency, database-level locking, transient vs permanent error classification, dead job management, and version-aware API differences across Sidekiq 6.5.x through 8.x. IMPORTANT: Before writing any Sidekiq job code, check the exact version in Gemfile.lock and load the docs via Context7 — the API changed significantly between major versions..
- Best trigger phrase: the request matches this skill.

## Explicit Invocation
- `Use $sidekiq-job-patterns when the request matches this skill.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
