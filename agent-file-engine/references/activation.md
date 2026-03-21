# Activation Guide

## Best-Fit Tasks
- Repository-specific AGENTS.md authoring and maintenance workflow.
- Best trigger phrase: creating, refreshing, or expanding AGENTS.md coverage for a codebase, including deciding whether nested AGENTS.md files are needed for subsystems with distinct rules, workflows, or AI-sensitive constraints.

## Explicit Invocation
- `Use $agent-file-engine when creating, refreshing, or expanding AGENTS.md coverage for a codebase, including deciding whether nested AGENTS.md files are needed for subsystems with distinct rules, workflows, or AI-sensitive constraints.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
