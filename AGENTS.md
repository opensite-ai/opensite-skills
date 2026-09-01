# OpenSite / Toastability — Agent Context

This file is the root context for all AI coding agents working in this repository set:
Codex, Cursor, Windsurf, Cline, GitHub Copilot, Perplexity Computer, and any other
engine that reads `AGENTS.md`. It covers the codebase, the complete catalog of **public**
skills, the memory workflow, the **private**-skill convention, and platform conventions
that must be preserved across every session.

---

## Organization Overview

| Org | Focus |
|-----|-------|
| `opensite-ai` | Semantic UI Engine libraries (`@opensite/ui`, `@page-speed/*`) |
| `Toastability` | Platform applications (`octane`, `toastability-service`, `app`, `dashtrack-ai`) |

---

## Primary Repositories

### Core Platform

- **`Toastability/octane`** — Rust + Axum AI API. The central service. All AI tasks,
  embeddings, semantic UI, and SEO analysis run here. **Rust 1.91+, Axum 0.8, Fly.io.**
- **`Toastability/toastability-service`** — Rails 6.1 primary API. Restaurant management
  platform. Owns the canonical PostgreSQL schema. **Ruby 3.3, Heroku.**
- **`Toastability/app`** — Next.js 16 CMS frontend (dashtrack-cms). The operator-facing
  dashboard. **React 19, Tailwind v4.**
- **`Toastability/dashtrack-ai`** — Rails 8.0.3 MCP connector. Function-based API.
  Shares the database with `toastability-service`.

### UI Libraries

- **`opensite-ai/opensite-ui`** — `@opensite/ui@3.x` — foundational component library
  (TSup + Tailwind v4 + Radix UI)
- **`opensite-ai/ui-library`** — Next.js showcase for the component library
- **`opensite-ai/page-speed-*`** — Sub-libraries: img, video, forms, router, skins,
  hooks, etc.

---

## Technology Stack

### Octane (Rust)
- Axum 0.8, Tokio async runtime
- deadpool-postgres + tokio-postgres + sqlx
- Anthropic API (Opus 4.6 for research, Sonnet 4.6 for generation)
- Voyage AI embeddings (migrating to self-hosted BGE-M3 + Qwen3-Embedding-8B)
- ONNX Runtime (U2-Net, Xception, etc.)
- Tigris S3 (object storage on Fly.io)
- Sentry 0.46.1 (structured JSON tracing)

### Rails Services
- Rails 6.1 (`toastability-service`) + Rails 8.0.3 (`dashtrack-ai`)
- Ruby 3.3, Sidekiq + Redis, PostgreSQL
- Heroku deployment, RSpec test suite

### Frontend
- Next.js 16, React 19, TypeScript 5
- Tailwind CSS v4 (CSS-first config, no `tailwind.config.js`)
- ShadCN UI (new-york style), Radix UI primitives
- CVA (class-variance-authority), tailwind-merge
- Vercel deployment

---

## Critical Rules — Never Violate These

1. **No PHI in logs** — Never log raw prompts, responses, emails, phone numbers, or
   any user-submitted content in production code. Hash prompt content before logging.

2. **Audit every LLM call** — All LLM provider calls in Octane must be wrapped with
   `AuditedLlmProvider`. This is a HIPAA requirement.

3. **No migrations in dashtrack-ai** — Only `toastability-service` owns the database
   schema. `dashtrack-ai` syncs with `bundle exec rake toast:schema:sync`.

4. **CSS variables, not hardcoded colors** — All UI components use CSS variable tokens
   (`bg-background`, `text-foreground`, etc.), never `bg-white` or `text-gray-900`.

5. **`AppError`, not `unwrap`** — All Octane handlers return `Result<Json<T>, AppError>`.
   Never use `.unwrap()` or `.expect()` in handler code.

6. **Typed state, not raw `Extension`** — Use typed state structs in Axum handlers,
   never `Extension<Pool>`.

7. **Fly.io private network** — Service-to-service calls use `{app}.internal:{port}`
   addresses, never public URLs.

8. **Tigris S3 endpoint** — Always `https://fly.storage.tigris.dev`, not AWS endpoints.

---

## Memory System — Persistent Long-Term Memory

This repo ships a four-skill memory system that gives you persistent long-term memory
across all sessions using only the local filesystem. **Use it on every non-trivial
session.** Zero external dependencies — Python 3.8+ only.

### The Four Memory Skills

| Skill | Role | When to Invoke |
|-------|------|----------------|
| `memory` | Core store, schema, scripts | Direct read/write/search operations |
| `memory-recall` | Load context before work begins | Start of every session |
| `memory-write` | Capture and persist session learnings | End of session / "save this" |
| `memory-consolidate` | Decay, deduplicate, compress old entries | Weekly or monthly |

### Memory Layers

| Layer | Directory | What Lives Here |
|-------|-----------|-----------------|
| Episodic | `memory/store/episodic/` | Session summaries, milestones, events |
| Semantic | `memory/store/semantic/` | Project facts, tech notes, user preferences, domain knowledge |
| Procedural | `memory/store/procedural/` | ADRs, workflows, code conventions |
| Working | `memory/store/working/active.md` | Hot-state handoff between sessions |

### Standard Session Workflow

```
┌─────────────────────────────────────────────────────┐
│  SESSION START                                       │
│  Invoke: memory-recall                               │
│  → loads working memory (active.md)                 │
│  → searches semantic, procedural, episodic layers   │
│  → delivers a structured context brief              │
├─────────────────────────────────────────────────────┤
│  DURING SESSION                                      │
│  Work normally with full historical context active  │
│  Invoke memory directly for ad-hoc reads/writes     │
├─────────────────────────────────────────────────────┤
│  SESSION END                                         │
│  Invoke: memory-write                                │
│  → extracts decisions, facts, preferences           │
│  → writes session summary (episodic)                │
│  → writes new facts (semantic)                      │
│  → writes ADRs and workflows (procedural)           │
│  → updates active.md for next-session handoff       │
├─────────────────────────────────────────────────────┤
│  WEEKLY / MONTHLY                                    │
│  Invoke: memory-consolidate                          │
│  → decays stale entries (high→medium→low→archived)  │
│  → detects duplicate titles                         │
│  → compresses old sessions into monthly summaries   │
│  → rebuilds the search index                        │
└─────────────────────────────────────────────────────┘
```

### Memory Scripts (direct use)

All scripts live in `memory/scripts/`. They are called by the memory skills automatically
but can also be invoked directly from Bash:

```bash
# Search across all memory layers
python memory/scripts/search_memory.py --query "axum middleware" --type semantic

# Write a new memory entry
python memory/scripts/write_memory.py \
  --type semantic --category technologies \
  --title "Axum Tower Middleware Pattern" \
  --content "When adding middleware in Axum 0.8+, use tower::ServiceBuilder..." \
  --tags "rust,axum,middleware,tower" --project octane

# Write an Architecture Decision Record
cat <<'EOF' | python memory/scripts/write_memory.py \
  --type procedural --category decisions \
  --title "ADR: Use Axum over Actix-Web" \
  --content-stdin \
  --tags "rust,axum,adr,architecture" --project octane
## Context
...

## Decision
...

## Rationale
...
EOF

# List all memories (brief mode)
python memory/scripts/list_memories.py --brief

# View store stats
python memory/scripts/search_memory.py --stats

# Run full maintenance
python memory/scripts/consolidate.py

# Dry-run maintenance (preview only)
python memory/scripts/consolidate.py --dry-run
```

For multiline markdown, code fences, or shell-sensitive text, prefer
`--content-stdin` with a heredoc or `--content-file` instead of inline `--content`.

### Memory Privacy

The store is local-only. The `memory/.gitignore` excludes all data files:
- `memory/store/episodic/`
- `memory/store/semantic/`
- `memory/store/procedural/`
- `memory/store/working/active.md`
- `memory/meta/index.json`

Only the skill instructions and scripts are versioned in git.

---

## Available Skills

Skills follow the [Agent Skills open standard](https://agentskills.io). Each skill
directory contains a `SKILL.md` with frontmatter and instructions. Invoke with
`/skill-name` (Codex, Cursor) or the platform's equivalent slash command. Each skill also
ships optional `references/`, `templates/`, `examples/`, and `scripts/` resources.

### Private Skills (this machine only)

> If a file named **`PRIVATE_SKILLS.md`** exists at the repo root, read it and treat every
> skill listed there as locally available, exactly like the public skills below. It is the
> canonical index of gitignored/proprietary skills. Do **not** copy its skill names,
> descriptions, or trigger text into committed files. If the file is absent (public
> clone), skip this step — only the public skills below apply.

### Memory System

| Skill | Invoke When |
|-------|-------------|
| `memory` | Direct read, write, or search operations on the memory store |
| `memory-recall` | Start of any non-trivial session or when asked "do you remember" |
| `memory-write` | End of session, after major decisions, after fixing a hard bug |
| `memory-consolidate` | Weekly/monthly maintenance of the memory store |

### Context Management

| Skill | Invoke When |
|-------|-------------|
| `context-management` | Long sessions, large tool outputs, after compaction, or when context window is low. FTS5 indexing, BM25 search, output compression, session checkpointing. |

### Growth & CRO

| Skill | Invoke When |
|-------|-------------|
| `ab-testing` | Plan/design A/B tests; build a growth experimentation program (hypotheses, ICE backlog, sample size, significance, velocity) |
| `analytics` | Set up/improve/audit analytics — GA4, GTM, event tracking, UTMs, tracking plans |
| `cro` | Optimize marketing pages & lead/contact forms (value prop, trust, friction); share a URL for feedback |
| `cro-optimization` | Hypothesis-driven CRO discipline: audit → hypothesize → test → decide |
| `experiment-design` | Design experiments that answer the question asked — hypothesis, sample size/MDE, duration, no-peeking |
| `form-strategy` | Design/audit forms for conversion, validation, spam resistance, and tooling choice |
| `funnel-flow-architecture` | Architect cross-tool funnels matched to audience & stage; orchestrates the other growth skills |
| `multi-step-form-design` | Multi-step forms: progress indicators, conditional logic, save-and-resume, staged patterns |
| `onboarding` | Optimize post-signup activation — time-to-value, "aha moment", activation models |
| `signup` | Optimize signup/registration/trial activation — reduce friction, raise completion |

### Design, UI & UX

| Skill | Invoke When |
|-------|-------------|
| `accessibility-audit` | WCAG 2.1 AA audit (perceivable/operable/understandable/robust) + remediation roadmap |
| `frontend-design` | Build distinctive production-grade interfaces; avoid generic "AI slop" aesthetics |
| `mobile-design` | Mobile-first iOS/Android/React Native/Flutter design thinking — touch, performance, platform conventions |
| `theme-factory` | Apply 10 preset color/font themes to slides/docs/pages, or generate a custom theme |
| `ui-design-system` | Design tokens, component docs, responsive calculations, and dev handoff for design systems |
| `ui-ux-pro-max` | Searchable UI/UX design-intelligence database (styles, palettes, typography, charts) → full design system |
| `ux-researcher-designer` | Personas, journey mapping, usability testing frameworks, and research synthesis |

### Strategy & Leadership

| Skill | Invoke When |
|-------|-------------|
| `ceo-advisor` | Executive strategy, board/investor relations, org culture, and financial scenario modeling |
| `product-strategist` | Head-of-Product work: OKR cascade, market/competitive analysis, vision, team scaling |

### Architecture & Data Science

| Skill | Invoke When |
|-------|-------------|
| `senior-architect` | Software architecture across React/Next/Node/React Native/Swift/Kotlin/Flutter/Go/Python — diagrams, decisions, trade-offs |
| `senior-data-scientist` | Statistical modeling, experiment design, feature engineering, causal inference, model evaluation |

### AI & Research

| Skill | Invoke When |
|-------|-------------|
| `ai-research-workflow` | Multi-step research (brand guide, market analysis) — WorkflowBuilder, Opus/Sonnet routing, `ai_tasks` |
| `ai-retrieval-patterns` | RAG / PageIndex / hybrid retrieval decision framework (Milvus, embedding models) |
| `deep-research-agent-architecture` | Design cited-research agents — planner/executor separation, source adapters, citation verification, cost caps |
| `enterprise-nl2sql-architecture` | NL2SQL over client-owned Postgres/MSSQL/MySQL/Oracle/Snowflake/BigQuery at hundreds-of-DBs scale |

### Productivity & Tooling

| Skill | Invoke When |
|-------|-------------|
| `planning-with-files` | Manus-style persistent markdown files for planning/tracking (`task_plan.md`, `notes.md`, deliverable) |
| `imagegen` | Generate/edit images via the OpenAI Image API through a bundled CLI |
| `hf-cli` | Hugging Face Hub CLI — download/upload/manage models, datasets, and Spaces |

### UI / Frontend

| Skill | Invoke When |
|-------|-------------|
| `opensite-ui-components` | `@opensite/ui@3.x` component library development |
| `tailwind4-shadcn` | Tailwind v4 config, ShadCN (new-york), theming |
| `page-speed-library` | `@page-speed/*` sub-library development |
| `semantic-ui-builder` | AI-powered site builder (Octane + CMS) |
| `client-side-routing-patterns` | Next.js / React router patterns |
| `react-rendering-performance` | Rendering optimization, memoization, profiling |

### Rails / Backend

| Skill | Invoke When |
|-------|-------------|
| `rails-query-optimization` | ActiveRecord query tuning, N+1 elimination, CTEs, `EXPLAIN ANALYZE` |
| `rails-zero-downtime-migrations` | Safe schema migrations with zero downtime |
| `sidekiq-job-patterns` | Background job design, retry logic, scheduling |

### Rust Patterns

| Skill | Invoke When |
|-------|-------------|
| `rust-async-patterns` | Tokio concurrency, task management, channels |
| `rust-error-handling` | `thiserror`, `anyhow`, error propagation patterns |

### Database / Infrastructure

| Skill | Invoke When |
|-------|-------------|
| `postgres-performance-engineering` | Query plans, index design, EXPLAIN ANALYZE |
| `pgvector-optimization` | pgvector index tuning, similarity search |

### Refactoring / Migrations

| Skill | Invoke When |
|-------|-------------|
| `large-scale-refactor` | Guardrails for 50+ file tasks — spec-gate, scope enforcement, drift detection, session handoff |
| `dependency-upgrade-orchestrator` | Safe multi-package upgrades across any ecosystem |

### DevOps / Operations

| Skill | Invoke When |
|-------|-------------|
| `agent-file-engine` | Authoring or auditing `AGENTS.md` / `CLAUDE.md` files |
| `git-workflow` | Branch naming, commits, PR conventions — explicit invoke only |
| `automation-builder` | Building agent automation workflows |

### Linux / Dev Environment

| Skill | Invoke When |
|-------|-------------|
| `linux-distro-selector` | Pick a distro + verify hardware/GPU fit (advisory) |
| `linux-install-planner` | Windows→Linux install runbook (advisory) |
| `linux-dev-workstation` | Configure a dev environment — GPU drivers, shell, editors, toolchains, dotfiles |
| `linux-ai-dev-stack` | AI toolchain — local LLM inference, coding agents, MCP servers, ML frameworks |

### Quality / Security

| Skill | Invoke When |
|-------|-------------|
| `code-review-security` | Security-focused PR reviews |
| `epistemic-rigor` | Anti-sycophantic, truth-first analysis — override approval-seeking behavior on hypotheses/decisions |

---

## Model Routing Guide

| Task | Recommended Model | Reason |
|------|-------------------|--------|
| Deep research, brand analysis, market research | Opus 4.6 | 1M context, strong reasoning, web search |
| Report generation, structured output | Sonnet 4.6 | Near-Opus performance, 5× cheaper |
| Security audits, architecture reviews | Opus 4.6 | High-stakes, deep reasoning required |
| Standard coding — bug fixes, features | Sonnet 4.6 | Near-parity for most coding tasks |
| Self-hosted inference (Phase 1+) | Llama 3.3 70B | SOC2/HIPAA compliant, $0.002–0.005/1K |

---

## Skill Invocation by Platform

| Platform | How to Invoke a Skill |
|----------|-----------------------|
| **Codex** | `/skill-name` or `$skill-name` |
| **Cursor** | `/skill-name` via the command palette |
| **Windsurf** | `/skill-name` |
| **Cline** | `/skill-name` |
| **GitHub Copilot** | `@skill-name` or via workspace instructions |
| **Perplexity Computer** | Skill auto-triggers from description match; explicit `@skill-name` |

Skills are installed via `setup.sh` (symlinks for local engines) or the cloud sync
scripts for Perplexity Computer and Claude Desktop:

```bash
./setup.sh              # symlink all skills for Claude Code, Codex, Cursor
./sync-perplexity.sh    # upload to Perplexity Computer cloud
./sync-claude.sh        # upload to Claude Desktop cloud
```

---

## Repo Structure

```
opensite-skills/
├── memory/                      ← Core memory store + Python scripts
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── write_memory.py
│   │   ├── search_memory.py
│   │   ├── list_memories.py
│   │   └── consolidate.py
│   └── store/                   ← Memory data (gitignored, local only)
│       ├── episodic/
│       ├── semantic/
│       ├── procedural/
│       └── working/
├── memory-recall/               ← Context retrieval agent skill
│   └── SKILL.md
├── memory-write/                ← Session capture agent skill
│   └── SKILL.md
├── memory-consolidate/          ← Maintenance agent skill
│   └── SKILL.md
├── <skill-name>/                ← One directory per skill
│   ├── SKILL.md                 ← Main skill instructions + frontmatter
│   ├── agents/openai.yaml       ← Codex/OpenAI metadata (invocation policy)
│   ├── references/activation.md ← Portable activation guide
│   ├── templates/               ← Optional task templates
│   ├── examples/                ← Optional sample outputs
│   └── scripts/                 ← Optional helper scripts
├── scripts/
│   ├── refresh_skill_support.py
│   └── validate_skills.py
├── AGENTS.md                    ← This file — context for all non-Claude agents
├── CLAUDE.md                    ← Claude Code specific context
├── PRIVATE_SKILLS.md            ← Private/gitignored skill index (local only, never committed)
├── README.md                    ← Human-readable setup + reference guide
├── setup.sh                     ← Symlink installer (local engines)
├── sync-perplexity.sh           ← Perplexity Computer cloud sync
├── sync-claude.sh               ← Claude Desktop cloud sync
└── .env                         ← Session cookies (gitignored)
```

---

## Structural Standards for Skills

Every skill follows the same portable baseline:

- `SKILL.md` — standard `name`, `description`, `version`, and `allowed-tools` frontmatter
- `agents/openai.yaml` — Codex UI metadata and implicit-invocation policy
- `references/activation.md` — portable activation guide with an explicit invocation example

Validate and refresh the full skill set with:

```bash
python3 scripts/refresh_skill_support.py
python3 scripts/validate_skills.py
```

---

## Platform Conventions — Always Preserve

These conventions are enforced across every service and must never be regressed:

| Convention | Rule |
|------------|------|
| PHI safety | No user content in logs; hash prompts before audit logging |
| Axum state | `State<Arc<HandlerState>>`, never `Extension<Pool>` |
| CSS tokens | `bg-background`, `text-foreground` — never hardcoded colors |
| SOC2 audit trail | Every LLM call wrapped in `AuditedLlmProvider` |
| Schema ownership | Migrations only in `toastability-service` |
| Fly.io networking | `{app}.internal:{port}` addresses for all internal calls |
| Object storage | `https://fly.storage.tigris.dev` endpoint for Tigris S3 |
| Error handling | `AppError` in all Axum handlers — no `.unwrap()` or `.expect()` |
