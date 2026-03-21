# Discovery Checklist

Use this checklist before writing or updating any `AGENTS.md`.

## Repo inventory

- Identify the repo root and whether it is a single project or a workspace.
- List existing `AGENTS.md`, `README.md`, `CLAUDE.md`, and major docs under `docs/`.
- Identify primary manifests:
  - `package.json`, `pnpm-workspace.yaml`, `turbo.json`
  - `Cargo.toml`
  - `Gemfile`
  - `pyproject.toml`
  - `go.mod`
- Identify major code roots: `src/`, `app/`, `components/`, `packages/`, `apps/`, `lib/`, `services/`, `workers/`, `jobs/`.

## Commands

Find the commands agents will actually need:

- test
- type-check
- lint
- build
- package or export generation
- app-specific smoke checks

Prefer commands from real manifests, CI, or package scripts over guesses.

## High-signal docs

Read the docs that most strongly constrain agent work:

- architecture overviews
- performance or bundle-size rules
- serialization contracts
- migration templates
- auth or deployment docs
- AI/vector/workflow docs

## Hotspots for nested coverage

Look for directories with:

- unique contracts or serialization rules
- AI-specific behavior
- performance-sensitive code
- deployment or infra logic
- background job patterns
- design-system or block-registry rules

If a directory is large but does not have unique rules, keep coverage at the parent level.
