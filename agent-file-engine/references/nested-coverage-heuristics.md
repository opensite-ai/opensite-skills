# Nested Coverage Heuristics

Use nested `AGENTS.md` files sparingly and intentionally.

## Add a nested file when

- The subtree has rules that do not belong in the root file.
- Agents repeatedly need local context to avoid mistakes.
- The subtree has its own verification commands or generation scripts.
- The subtree has special contracts: JSON-only payloads, registry metadata, vector schema rules, performance budgets, auth boundaries, or migration safety rules.
- The subtree is a major subsystem with independent workflows.

## Do not add a nested file when

- The subtree just mirrors the parent rules.
- The directory is small and shallow.
- The only local guidance is naming or minor style preferences.
- The same guidance is already expressed clearly in the parent file.

## Good candidates

- `components/blocks/`
- `src/services/orchestration/`
- `app/services/ai/`
- `jobs/` or `workers/`
- `site_builder_manager/`
- `vectorization/`
- `packages/<name>/` in a monorepo when a package has special rules

## Bad candidates

- utility folders with no special workflows
- directories containing only a handful of thin wrappers
- folders where a local `README.md` already captures the necessary delta and the parent AGENTS can simply reference it

## Coverage strategy

1. Root file first.
2. Add nested files only for high-signal subtrees.
3. Keep nested files short and local.
4. Link to the nested files from the root AGENTS when they exist.

The goal is not maximum file count. The goal is maximum agent clarity per token.
