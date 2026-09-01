# OpenSite Agent Skills — Claude Code Context

This `CLAUDE.md` is the root context file for Claude Code sessions in this skills repo.
It covers the memory workflow, the complete catalog of **public** skills, model routing
guidance, and the convention for **private** skills.

> **Using this in your own project?** The Memory System and Available Skills sections are
> the reusable core. Replace the Organization / Repositories section with your own
> codebase details.

---

## Organization & Repositories

| Org | Focus |
|-----|-------|
| `opensite-ai` | Semantic UI Engine libraries (`@opensite/ui`, `@page-speed/*`) |
| `Toastability` | Platform applications (`octane`, `toastability-service`, `app`, `dashtrack-ai`) |

- **`Toastability/octane`** — Rust + Axum AI API (the central service). Rust 1.91+, Axum 0.8, Fly.io.
- **`Toastability/toastability-service`** — Rails 6.1 primary API. Owns the canonical PostgreSQL schema. Ruby 3.3, Heroku.
- **`Toastability/app`** — Next.js 16 CMS frontend (dashtrack-cms). React 19, Tailwind v4.
- **`Toastability/dashtrack-ai`** — Rails 8.0.3 MCP connector. Shares the database with `toastability-service`.

---

## 🧠 Memory System — Core Workflow

This repo ships a four-skill persistent memory engine. **Use it every session, without
exception.** It is your primary mechanism for maintaining continuity across conversations.

### Session Protocol

```
START OF SESSION         →  /memory-recall
  ↓ (work happens)
END OF SESSION           →  /memory-write
  ↓ (weekly or after bulk writes)
MAINTENANCE              →  /memory-consolidate
```

**Never start non-trivial work without running `/memory-recall` first.** It loads your
working memory handoff, project context, architecture decisions, conventions, and recent
session history before a single line of code is touched.

**Never end a session without running `/memory-write`.** It extracts decisions, facts,
and outcomes from the conversation and writes them to the correct memory layer so the
next session can pick up exactly where this one left off.

### Memory Skills

| Skill | Role | Invoke When |
|-------|------|-------------|
| `memory` | Core store — schema, scripts, direct read/write/search | Anytime you need raw memory access |
| `memory-recall` | Context retrieval — loads all relevant history before work | **Every session start** / "do you remember" |
| `memory-write` | Session capture — extracts and persists session learnings | **Every session end** / "save this" / "remember this" |
| `memory-consolidate` | Maintenance — decay, dedup, compress old sessions | Weekly or after bulk writes |

### Memory Layers

| Layer | Path | What Goes Here |
|-------|------|----------------|
| Episodic | `memory/store/episodic/` | Session summaries, milestones, breakthroughs |
| Semantic | `memory/store/semantic/` | Project facts, tech notes, user preferences, domain knowledge |
| Procedural | `memory/store/procedural/` | ADRs, workflows, code conventions |
| Working | `memory/store/working/active.md` | Hot context handoff between sessions |

### Inline Memory Commands

```
"save this"              →  /memory-write   (captures current conversation state)
"remember this"          →  /memory-write
"do you remember X?"     →  /memory-recall  (targeted recall for X)
"store to memory"        →  /memory-write
```

### What to Write

**Always write:** architecture decisions with rationale (ADRs); non-trivial bugs (root
cause + fix + why); new file paths, data models, or API contracts; explicit user
preferences; repeatable workflows.

**Write selectively:** technology facts (versions, library gotchas, confirmed behaviors);
project-specific knowledge not obvious from code.

**Never write:** trivial edits; facts already in the codebase and greppable; duplicates —
always search before writing.

### Data Privacy

The memory store (`memory/store/`) is gitignored and lives only on this machine. It is
never committed. Only the skill instruction files and Python scripts are versioned.

---

## Available Skills

Skills live in the top-level directories of this repo and are symlinked into
`~/.claude/skills/`. Load with `/skill-name` or let Claude trigger them automatically
from context. Each skill has its own `SKILL.md` plus optional `references/`, `templates/`,
`examples/`, and `scripts/`.

### Private Skills (this machine only)

> If a file named **`PRIVATE_SKILLS.md`** exists at the repo root, read it and treat every
> skill listed there as locally available, exactly like the public skills below. Do **not**
> copy its skill names, descriptions, or trigger text into committed files (this
> `CLAUDE.md`, `README.md`, or any public skill). If the file is absent (public clone),
> skip this step — only the public skills below apply.

### Memory (Core — Use Every Session)

| Skill | When to Use |
|-------|-------------|
| `memory-recall` | **Start of every session** — loads full context before work begins |
| `memory-write` | **End of every session** — persists decisions, facts, and outcomes |
| `memory` | Direct memory store access — search, read, or write entries manually |
| `memory-consolidate` | Weekly maintenance — decay, dedup, compress old sessions |

### Context Management

| Skill | When to Use |
|-------|-------------|
| `context-management` | Long sessions, large tool outputs, after compaction, context window low. FTS5 indexing, BM25 search, output compression, session checkpointing. |

### Growth & CRO

| Skill | When to Use |
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

| Skill | When to Use |
|-------|-------------|
| `accessibility-audit` | WCAG 2.1 AA audit (perceivable/operable/understandable/robust) + remediation roadmap |
| `frontend-design` | Build distinctive production-grade interfaces; avoid generic "AI slop" aesthetics |
| `mobile-design` | Mobile-first iOS/Android/React Native/Flutter design thinking — touch, performance, platform conventions |
| `theme-factory` | Apply 10 preset color/font themes to slides/docs/pages, or generate a custom theme |
| `ui-design-system` | Design tokens, component docs, responsive calculations, and dev handoff for design systems |
| `ui-ux-pro-max` | Searchable UI/UX design-intelligence database (styles, palettes, typography, charts) → full design system |
| `ux-researcher-designer` | Personas, journey mapping, usability testing frameworks, and research synthesis |

### Strategy & Leadership

| Skill | When to Use |
|-------|-------------|
| `ceo-advisor` | Executive strategy, board/investor relations, org culture, and financial scenario modeling |
| `product-strategist` | Head-of-Product work: OKR cascade, market/competitive analysis, vision, team scaling |

### Architecture & Data Science

| Skill | When to Use |
|-------|-------------|
| `senior-architect` | Software architecture across React/Next/Node/React Native/Swift/Kotlin/Flutter/Go/Python — diagrams, decisions, trade-offs |
| `senior-data-scientist` | Statistical modeling, experiment design, feature engineering, causal inference, model evaluation |

### AI & Research

| Skill | When to Use |
|-------|-------------|
| `ai-research-workflow` | Multi-step research orchestration (WorkflowBuilder, Opus/Sonnet routing, `ai_tasks` persistence) |
| `ai-retrieval-patterns` | RAG / PageIndex / hybrid retrieval decision framework (Milvus, embedding models) |
| `deep-research-agent-architecture` | Design cited-research agents — planner/executor separation, source adapters, citation verification, cost caps |
| `enterprise-nl2sql-architecture` | NL2SQL over client-owned Postgres/MSSQL/MySQL/Oracle/Snowflake/BigQuery at hundreds-of-DBs scale |

### Productivity & Tooling

| Skill | When to Use |
|-------|-------------|
| `planning-with-files` | Manus-style persistent markdown files for planning/tracking (`task_plan.md`, `notes.md`, deliverable) |
| `imagegen` | Generate/edit images via the OpenAI Image API through a bundled CLI |
| `hf-cli` | Hugging Face Hub CLI — download/upload/manage models, datasets, and Spaces |

### UI / Frontend

| Skill | When to Use |
|-------|-------------|
| `opensite-ui-components` | `@opensite/ui@3.x` component patterns — block/skin architecture, Radix UI, Tailwind v4 |
| `tailwind4-shadcn` | Tailwind v4 + ShadCN config, CSS variables, theming, v3→v4 migration |
| `page-speed-library` | `@page-speed/*` sub-library development (tsup, peer dependencies) |
| `semantic-ui-builder` | AI-powered site builder patterns (Octane + CMS) |
| `client-side-routing-patterns` | History API / SPA routing hooks |
| `react-rendering-performance` | React 19 Compiler, profiler-driven optimization, `useTransition`, memoization |

### Rails / Backend

| Skill | When to Use |
|-------|-------------|
| `rails-query-optimization` | N+1 beyond `includes`, CTEs, lateral joins, `EXPLAIN ANALYZE`, counter caches |
| `rails-zero-downtime-migrations` | Hot-compatibility schema changes on live PostgreSQL |
| `sidekiq-job-patterns` | Idempotency, locking, error classification, version-aware API (6.5.x–8.x) |

### Rust / Backend

| Skill | When to Use |
|-------|-------------|
| `rust-async-patterns` | Tokio concurrency, `Send` bounds, `CancellationToken`, timeout composition |
| `rust-error-handling` | `thiserror` vs `anyhow`, error hierarchy design, handler mapping |

### Database / Performance

| Skill | When to Use |
|-------|-------------|
| `pgvector-optimization` | HNSW/IVFFlat tuning, scalar/binary quantization, dimensionality compression |
| `postgres-performance-engineering` | Query plan instability, statistics, GIN pending list, PgBouncer, autovacuum |

### Refactoring / Migrations

| Skill | When to Use |
|-------|-------------|
| `large-scale-refactor` | Guardrails for 50+ file tasks — spec-gate, scope enforcement, drift detection, session handoff |
| `dependency-upgrade-orchestrator` | Safe multi-package upgrades across any ecosystem (Cargo, npm, pip, Go, Maven, Bundler) |

### DevOps / Operations

| Skill | When to Use |
|-------|-------------|
| `agent-file-engine` | Author or audit `AGENTS.md` / `CLAUDE.md` files |
| `git-workflow` | Branch naming, commit conventions, PRs, CI — explicit invoke only |
| `automation-builder` | Playwright/browser automation, file uploads, media tooling (ffmpeg, ImageMagick, Sharp) |

### Linux / Dev Environment

| Skill | When to Use |
|-------|-------------|
| `linux-distro-selector` | Pick a distro + verify hardware/GPU fit (advisory) |
| `linux-install-planner` | Windows→Linux install runbook (advisory) |
| `linux-dev-workstation` | Configure a dev environment — GPU drivers, shell, editors, toolchains, dotfiles |
| `linux-ai-dev-stack` | AI toolchain — local LLM inference, coding agents, MCP servers, ML frameworks |

### Quality / Security

| Skill | When to Use |
|-------|-------------|
| `code-review-security` | Security-focused PR review — PHI leaks, injection, auth, SSRF, unsafe Rust |
| `epistemic-rigor` | Anti-sycophantic, truth-first analysis — override approval-seeking behavior on hypotheses/decisions |

---

## Model Routing Guide

| Task | Model | Why |
|------|-------|-----|
| Deep research, analysis, architecture review | Opus 4.6 | 1M context, strong reasoning, web search |
| Report generation, structured output | Sonnet 4.6 | Near-Opus performance, 5× cheaper |
| Security audits, high-stakes decisions | Opus 4.6 | Deep reasoning required |
| Standard coding — bug fixes, features | Sonnet 4.6 | Near-parity for most coding tasks |
| Self-hosted inference | Llama 3.3 70B | SOC2/HIPAA compliant, low cost |

---

## Cloud Skill Sync

Skills in this repo are the source of truth. Claude Code reads them via symlinks
(changes are instant). Cloud platforms require a re-upload after edits:

```bash
./sync-perplexity.sh    # Perplexity Computer — perplexity.ai/account/org/skills
./sync-claude.sh        # Claude Desktop     — claude.ai/customize/skills
```

Both scripts open a **visible Brave browser window** and automate the upload UI.
Credentials live in `.env` (gitignored):

```bash
PERPLEXITY_SESSION_COOKIE=...   # from perplexity.ai cookies: __Secure-next-auth.session-token
CLAUDE_SESSION_COOKIE=...       # from claude.ai cookies: sessionKey
```

**Important implementation notes (do not regress):**

- Both scripts use the real Brave binary (`/Applications/Brave Browser.app`) in headed
  (visible) mode — Playwright's bundled headless Chromium is detected and blocked by
  Cloudflare on both sites.
- File upload uses Playwright's `filechooser` event interception after clicking the
  upload zone — directly setting `input.files` via the DOM does not trigger React's
  `onChange` and silently fails.
- Both scripts create a fresh browser context (not your existing Brave profile) and
  inject only the session cookie.

**Update strategies differ between platforms:**

- **Perplexity** (`sync-perplexity.sh`): searches the skill list first; if found, opens
  the skill's `⋮` menu and clicks the update option; if not found, clicks "Upload skill".
  Drop-zone element: `div[role="button"]` with text "Drag your file here or click to upload".
- **Claude** (`sync-claude.sh`): always runs the same "new skill" flow (`+` button →
  "Upload a skill"); if the skill exists Claude shows "Replace [name] skill?" — the script
  clicks "Upload and replace". No search or `⋮` menu needed.
  Drop-zone element: `<button>` with text "Drag and drop or click to upload".
