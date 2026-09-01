<!--
  AGENTS.md — cross-tool agent instructions (the emerging standard).
  Read by Codex, Gemini CLI, aider, Goose, OpenCode, Zed, Warp, Cursor, VS Code, and more.

  Claude Code reads CLAUDE.md natively. Keep ONE source of truth by symlinking:
      ln -s AGENTS.md CLAUDE.md
  Then edit only this file. Keep it concise and high-signal; nested per-subsystem
  AGENTS.md files override/merge (closest file wins).
-->

# Agent Instructions

## Project overview
<!-- One or two sentences: what this project is and its primary language/framework. -->
TODO: describe the project.

## Build, test, and run commands
<!-- The exact commands an agent should use. Prefer the project's own gates. -->
- Install: `TODO`
- Build: `TODO`
- Test: `TODO`
- Lint / format: `TODO`
- Run locally: `TODO`

## Conventions
- Language/style: TODO (e.g. formatter + linter, import order, naming).
- Commit style: TODO (e.g. Conventional Commits).
- Branching: TODO (e.g. feature branches off `main`; never commit to `main`).

## Guardrails (safety)
- Never run destructive commands without explicit confirmation: `rm -rf`,
  `git push --force`, `git reset --hard`, database drops, package publishes.
- Do not read or print secrets. Secrets live outside the repo and are injected at
  runtime (e.g. `op run -- <cmd>`). Do not commit `.env` or tokens.
- Prefer plan mode / read-only exploration before large multi-file edits.
- Ask before opening firewall ports or binding a service to `0.0.0.0`.

## Model routing (optional)
- Cheap/read-only tasks (search, tests, classification): a small or local model.
- Everyday coding: mid-tier model. Architecture/review: top-tier model.
- Local model endpoint (if configured): `http://localhost:11434/v1` (Ollama).

## Notes for humans
- This file is the single source of truth for all agents. `CLAUDE.md` is a symlink to it.
