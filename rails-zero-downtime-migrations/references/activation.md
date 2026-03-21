# Activation Guide

## Best-Fit Tasks
- Zero-downtime database migration patterns for Rails 6.1+ on PostgreSQL with Heroku deployments. Covers the hot-compatibility principle, concurrent index creation, multi-step column operations, constraint validation strategies, and Heroku-specific release phase coordination.
- Best trigger phrase: adding columns, indexes, constraints, or renaming/removing any database object on a live production database.

## Explicit Invocation
- `Use $rails-zero-downtime-migrations when adding columns, indexes, constraints, or renaming/removing any database object on a live production database.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
