---
name: agent-file-engine
description: >
  Repository-specific AGENTS.md authoring and maintenance workflow. Use when
  creating, refreshing, or expanding AGENTS.md coverage for a codebase,
  including deciding whether nested AGENTS.md files are needed for subsystems
  with distinct rules, workflows, or AI-sensitive constraints.
compatibility: >
  Requires filesystem access to the target repository; shell access is strongly
  preferred for inventorying manifests, docs, tests, and existing AGENTS.md
  coverage.
metadata:
  opensite-category: ops
  opensite-scope: shared
  opensite-visibility: public
allowed-tools: "Read Grep Glob Bash"
---
# Agent File Engine

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before deciding AGENTS.md boundaries for large or safety-critical repos.
- Reference: [references/discovery-checklist.md](references/discovery-checklist.md)
- Reference: [references/nested-coverage-heuristics.md](references/nested-coverage-heuristics.md)
- Template: [templates/root-agents.md](templates/root-agents.md)
- Template: [templates/nested-agents.md](templates/nested-agents.md)
- Example: [examples/coverage-plan.md](examples/coverage-plan.md)
- Helper: `scripts/inventory_agent_scope.py`

## Task Focus for $ARGUMENTS
When this skill is invoked explicitly, treat `$ARGUMENTS` as the repo root or subtree that needs AGENTS.md coverage.

## Purpose

Use this skill to create or update AGENTS.md files that help AI coding agents navigate a repository safely, quickly, and consistently.

The output should be specific to the target codebase. Avoid generic “best practices” prose unless it is tied directly to the repo’s structure, build system, workflows, or risk areas.

## Scope Model

- A root `AGENTS.md` applies to the entire repository subtree beneath it.
- A nested `AGENTS.md` applies only to the subtree rooted at its directory.
- More deeply nested `AGENTS.md` files override parent instructions when they conflict.
- Nested files should add **local delta rules**, not restate the entire parent document.

This precedence model matters. Only add nested files when a subtree genuinely needs instructions that differ from or go beyond the parent.

## Workflow

1. Resolve the target repository.
   - Use the current working directory unless `$ARGUMENTS` points to another repo root or subtree.
   - If the request targets a nested path, still inspect the repo root before writing a local file.

2. Inventory the repository before writing anything.
   - Run `scripts/inventory_agent_scope.py <repo-path>` first.
   - Read existing `AGENTS.md` files, top-level manifests, README/docs, CI config, and a representative sample of core code paths.

3. Build a mental model of the codebase.
   - Identify the primary languages, frameworks, package managers, and test/lint/build commands.
   - Identify the risk areas: auth, data access, AI integrations, performance-sensitive code, design systems, deployment paths, migrations, and background jobs.
   - Identify whether the repo is a library, an app, a monorepo, or a mixed workspace.

4. Decide the AGENTS.md coverage plan.
   - Always evaluate root coverage first.
   - Add nested files only when a subtree has distinct invariants, workflows, or verification steps that would otherwise clutter the root file.
   - Prefer a small number of high-signal nested files over broad recursive coverage.

5. Create or update the root `AGENTS.md`.
   - The root file should explain the overall architecture, golden rules, key directories, common workflows, and minimum verification commands.
   - It should also point agents to nested `AGENTS.md` files when they exist.

6. Create or update nested `AGENTS.md` files only where warranted.
   - Scope them tightly to the subtree.
   - Make them more specific than the parent.
   - Focus on local conventions, contracts, performance constraints, serialization rules, integration rules, and test commands.

7. Validate the result.
   - Ensure every referenced path or doc exists.
   - Ensure parent and child files do not contradict each other.
   - Keep the files concrete: real paths, real commands, real workflows.

## Root AGENTS.md Requirements

The root file should usually contain:

- A one-paragraph mental model of the repo
- Golden rules that are non-obvious and high-signal
- Key directories and why they matter
- Common agent workflows
- Verification commands
- Notes about nested `AGENTS.md` files, if present

Keep it specific. “Run tests” is weak. “Run `pnpm test` and `pnpm type-check`” is useful.

## Nested AGENTS.md Requirements

A nested file is justified when the subtree has at least one of these:

- Distinct serialization or API contracts
- Different build or verification commands
- Specialized architecture or domain constraints
- High-risk performance, security, or AI workflows
- Strong local patterns that agents repeatedly get wrong

Examples from your codebases:

- `components/blocks/*` in `@opensite/ui` needs block-specific serialization, registry, and design-system rules.
- `src/services/orchestration/*` in `octane` needs workflow-step, memory, and side-effect boundaries.
- `app/services/ai/*` in Rails repos needs webhook, vector, and processor-specific rules.

Do **not** create nested files for shallow folders that add no new information.

## Writing Rules

- Prefer imperative, testable guidance.
- Use real file paths and command names.
- Call out forbidden changes explicitly when they matter.
- Keep parent files broad and nested files local.
- Avoid organizational lore that cannot be verified from the repo.
- If the repo already has strong AGENTS.md files, preserve the tone and structure unless they are clearly inconsistent or stale.

## Quality Bar

Before finishing, confirm:

- The root file reflects the actual repo, not a template
- Nested files exist only where they improve agent outcomes
- Commands and referenced docs exist
- The file set gives agents enough context to work without reading the whole repo every time
