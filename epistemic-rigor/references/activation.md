# Activation Guide — epistemic-rigor

## Best-Fit Tasks

Use this skill whenever you want honest critical analysis over agreement:

- Proposing a software architecture or API design
- Presenting a hypothesis or theory you want stress-tested
- Asking for evaluation of a code approach before investing in it
- Requesting an opinion where you need accuracy, not validation
- Any session where you've noticed the agent agreeing too readily

## Explicit Invocation

### Claude Code
```
/epistemic-rigor review my proposed Axum middleware design
```
```
@epistemic-rigor my hypothesis is that using a single Postgres connection pool
across all Axum worker threads is the bottleneck here
```

### Codex
```
$epistemic-rigor evaluate this API versioning strategy
```

### Cursor / Copilot / OpenCode
```
/epistemic-rigor
```
Then proceed with your proposal or question on the next line.

### Perplexity Computer (cloud skill)
Upload this skill to `perplexity.ai/account/org/skills`. Once active, trigger
phrases like "review my design", "is my hypothesis correct", or "validate my
thinking" will auto-activate it.

### Claude Desktop (cloud skill)
Upload to `claude.ai/customize/skills`. The skill loads automatically on
hypothesis and evaluation framing.

## Global Activation (Recommended)

For Claude Code, add to `~/.claude/CLAUDE.md` or your project's `CLAUDE.md`:
```markdown
## Behavioral Baseline
Load the `epistemic-rigor` skill for all sessions. Apply its Rigor Protocol
to any hypothesis, design, or evaluation I present.
```

For Codex, add to `~/.codex/instructions.md`:
```markdown
Apply $epistemic-rigor behavioral directives globally. Prioritize truth and
honest critical analysis over approval. When I propose a design or hypothesis,
find errors first, then strengths.
```

## Cross-Agent Notes

- This skill is purely instructional — no tools, filesystem access, or scripts.
  It loads and applies in any context window regardless of platform.
- The skill targets a structural training defect (RLHF sycophancy) rather than
  a task domain. It is intentionally global in scope rather than task-scoped.
- No conflict with other skills. It sets a behavioral baseline; other skills
  add domain-specific capabilities on top of it.
- On platforms without implicit invocation, invoke explicitly at the start of
  any session where critical evaluation is important.
