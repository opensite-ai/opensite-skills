# AI Coding Agent Skills + Multi Agent Support

## Single source of truth for a comprehensive, continually updating set of AI coding agent skills

![Multi Agent Support AI Skills Library](https://octane.cdn.ing/api/v1/images/transform?url=https://cdn.ing/assets/i/r/297562/3b1o40e6650ce6yxbgdcrr83c35e/og.jpg&f=webp)

A growing collection of skills spanning frontend design, Rust and Rails backend engineering, AI/RAG pipeline patterns, database performance, DevOps automation, and more — built to stay in sync across every AI coding agent you run. Because keeping Claude Code, Codex, Copilot, Cursor, and cloud platforms all individually up to date sounds like a special kind of hell, this repo ships a full set of scripts that maintain a single source of truth for all of them.

These skills follow the [Agent Skills open standard](https://agentskills.io) and are compatible with:

| Platform | Skill Location | Load method |
| ---------- | --------------- | ------------- |
| **Claude Code** | `~/.claude/skills/` (global) or `.claude/skills/` (project) | Automatic + `/skill-name` |
| **Claude Desktop** | Cloud upload — `claude.ai/customize/skills` | Automatic trigger |
| **Codex** | `~/.codex/skills/` (global) or `.agents/skills/` (repo) | Automatic + `$skill-name` |
| **GitHub Copilot** | `~/.copilot/skills/` (global) | Via `/` commands |
| **Perplexity Computer** | Cloud upload — `perplexity.ai/account/org/skills` | Automatic trigger |
| **Cursor** | `.cursor/skills/` per-repo | Via `/` commands |

> **One repo, zero copying.** Set this up once with the platform setup script and all tools read from the same directory via symlinks. Update a skill once — all tools see the change instantly.

---

## Quick Setup

> For local platforms: Claude Code, Codex, Cursor, and GitHub Copilot. Dedicated scripts for cloud platforms (Perplexity, Claude Desktop) below.

```bash
# 1. Clone to a stable location
git clone git@github.com:opensite-ai/opensite-skills.git ~/opensite-skills
cd ~/opensite-skills

# 2. Run the setup script
./setup.sh
```

The setup script detects which platforms are installed and creates symlinks from each platform's skills directory to this repo — no file copying.

---

## Memory System — Persistent Long-Term Context

This repo ships four skills that give any AI engine **persistent memory across sessions** using only the local filesystem. No external services, no databases, no pip installs — just Python 3.8+ and markdown files.

### The Four Memory Skills

| Skill | Role | When to Invoke |
|-------|------|----------------|
| `memory` | Core store — schema, scripts, direct read/write/search | Direct memory operations |
| `memory-recall` | Loads relevant context before work begins | **Start of every session** |
| `memory-write` | Extracts and persists session learnings | **End of every session** |
| `memory-consolidate` | Decays, deduplicates, compresses old entries | Weekly or monthly |

### Memory Layers

The store lives at `memory/store/` and is organized into four cognitive layers:

| Layer | Directory | What Goes Here |
|-------|-----------|----------------|
| **Episodic** | `store/episodic/` | Session summaries, milestones, breakthrough events |
| **Semantic** | `store/semantic/` | Project facts, tech notes, user preferences, domain knowledge |
| **Procedural** | `store/procedural/` | ADRs, repeatable workflows, code conventions |
| **Working** | `store/working/active.md` | Hot context handoff — current task, next steps, open questions |

### Standard Session Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  SESSION START                                              │
│  /memory-recall   ← loads working memory + relevant context │
│                                                             │
│  [... do your work ...]                                     │
│                                                             │
│  SESSION END                                                │
│  /memory-write    ← captures decisions, facts, next steps   │
└─────────────────────────────────────────────────────────────┘

Weekly / Monthly:
  /memory-consolidate  ← decays stale entries, deduplicates, compresses
```

#### What `memory-recall` loads

1. `store/working/active.md` — always first; the hot state from last session
2. Semantic memories relevant to the current project and technology keywords
3. Architecture Decision Records (ADRs) for the active project
4. Code conventions and workflows for the active project
5. The 3 most recent episodic session summaries

#### What `memory-write` saves

- **Episodic** — a session summary (goal, outcome, decisions, blockers, next steps)
- **Semantic** — project facts, tech gotchas, confirmed library behaviors, user preferences
- **Procedural** — ADRs with full Context / Decision / Rationale / Trade-offs / Status format
- **Working** — updated `active.md` with the next-session handoff state

#### Duplicate prevention

Before writing, `memory-write` searches the store and scores similarity:

| Score | Action |
|-------|--------|
| > 0.80 | Update the existing entry |
| 0.40 – 0.80 | Create new entry with a `related:` note |
| < 0.40 | Create a fresh entry |

### Memory Store Privacy

All store data lives only on your local machine. The `memory/.gitignore` file excludes every `store/` path from version control — only the skill instructions and Python scripts are committed to git.

To sync across machines, use a private git repo just for `memory/store/`, rsync in your backup system, or a dotfiles manager.

### Memory Store Maintenance

```bash
# Preview what consolidation would change (no writes)
python memory/scripts/consolidate.py --dry-run

# Full maintenance pass (decay + dedup + compress + reindex)
python memory/scripts/consolidate.py

# Manual search
python memory/scripts/search_memory.py --query "axum middleware" --type semantic
python memory/scripts/search_memory.py --stats

# Manual write
python memory/scripts/write_memory.py \
  --type semantic --category technologies \
  --title "Axum Tower Middleware Pattern" \
  --content "When adding middleware in Axum 0.8+..." \
  --tags "rust,axum,middleware" --project my-project

# Multiline / markdown-safe write
cat <<'EOF' | python memory/scripts/write_memory.py \
  --type procedural --category decisions \
  --title "ADR: Use thiserror for library error types" \
  --content-stdin \
  --tags "rust,error-handling,adr,architecture" --project my-project
## Context
...

## Decision
...
EOF
```

---

## Cloud Platform Sync

Both Perplexity Computer and Claude Desktop store skills in the cloud and require browser-based upload (neither has a public API). The sync scripts use **Playwright driving your real Brave browser** (headed, visible window) to bypass Cloudflare bot detection that blocks headless automation.

### Prerequisites

1. **Node.js 18+** — for Playwright
2. **Brave Browser** — must be installed at `/Applications/Brave Browser.app`
3. **Session cookies** — one per cloud platform (see below)

### Getting session cookies

Both scripts authenticate by injecting a session cookie into a fresh browser context. To get your cookie:

1. Open the target site in Brave and log in
2. Press `F12` → **Application** tab → **Cookies** → select the site domain
3. Find and copy the session token value (see per-platform details below)
4. Add to `.env` in this repo

`.env` format (copy from `.env.example`):
```bash
PERPLEXITY_SESSION_COOKIE="<value>"
CLAUDE_SESSION_COOKIE="<value>"
```

---

### Perplexity Computer

**Cookie to grab:** Open Brave → `perplexity.ai` → log in → `F12` → **Application** → **Cookies** → `https://www.perplexity.ai` → find `__Secure-next-auth.session-token`, copy its Value.

**URL used by the script:** `https://www.perplexity.ai/account/org/skills`

```bash
./sync-perplexity.sh                    # sync all skills
./sync-perplexity.sh --changed-only     # only git-modified skills since last commit
./sync-perplexity.sh rails-query-optimization  # one specific skill by name
```

**What it does per skill:**

1. Navigates to the org skills page
2. Searches the skill list for the skill name
3. **Exists** → opens the skill's `⋮` menu → clicks the update option → re-uploads the zip
4. **New** → clicks "Upload skill" → uploads the zip
5. Confirms modal closed (success) or reports the error message

**File upload mechanism:** Playwright intercepts the native `filechooser` event that fires when the dropzone is clicked. This triggers React's `onChange` correctly — directly setting `input.files` on the DOM does not work with React's synthetic event system and silently fails.

**Why Brave (not headless Chromium):** Playwright's bundled test Chromium has a distinct fingerprint Cloudflare detects and blocks after the first request. Using the real Brave binary (`/Applications/Brave Browser.app`) with a visible window passes Cloudflare's bot checks.

Or upload manually: go to `perplexity.ai/account/org/skills` → **Upload skill**, drag in any `SKILL.md` or `.zip` of the skill folder. Max 10 MB per upload.

---

### Claude Desktop

**Cookie to grab:** Open Brave → `claude.ai` → log in → `F12` → **Application** → **Cookies** → `https://claude.ai` → find `sessionKey`, copy its Value.

**URL used by the script:** `https://claude.ai/customize/skills`

```bash
./sync-claude.sh                    # sync all skills
./sync-claude.sh --changed-only     # only git-modified skills since last commit
./sync-claude.sh rails-query-optimization  # one specific skill by name
```

**What it does per skill:**
1. Navigates to `claude.ai/customize/skills`
2. Clicks the `+` (Add skill) button — a Radix dropdown trigger (`aria-label="Add skill"`)
3. Clicks **Upload a skill** in the dropdown (`[role="menuitem"]`)
4. Intercepts the `filechooser` event on the dashed upload zone and sets the zip file
5. **If the skill already exists**, Claude automatically shows a **"Replace [name] skill?"** confirmation dialog — the script clicks **Upload and replace** to proceed
6. **If the skill is new**, the modal closes on its own after upload

No manual duplicate detection or ⋮ menu navigation needed — Claude handles name collisions natively. The script runs the identical flow for every skill regardless of whether it exists.

**Why Brave (same reason as Perplexity):** Cloudflare on `claude.ai` also detects and blocks Playwright's bundled headless Chromium.

Or upload manually: go to `claude.ai/customize/skills` → click the **+** icon → **Upload a skill**, drag in a `SKILL.md` or `.zip`.

---

### Why not use my existing Brave login?

The scripts launch Brave with a **fresh browser context** (no profile, no cookies) and inject just the session cookie. This is intentional:

- Avoids touching or corrupting your actual Brave profile
- Works even if Brave is already open
- Session cookie gives full authenticated access without needing a full profile copy

If Brave is not installed, the scripts fall back to Playwright's bundled Chromium — but note that Cloudflare may block this on some networks.

---

## Manual Setup

### Claude Code (global)

```bash
mkdir -p ~/.claude/skills
for skill in ~/opensite-skills/*/; do
  skill_name=$(basename "$skill")
  ln -sfn "$skill" ~/.claude/skills/"$skill_name"
done
# Optional: symlink CLAUDE.md
ln -sfn ~/opensite-skills/CLAUDE.md ~/.claude/CLAUDE.md
```

### Codex (global)

```bash
mkdir -p ~/.codex/skills
for skill in ~/opensite-skills/*/; do
  skill_name=$(basename "$skill")
  ln -sfn "$skill" ~/.codex/skills/"$skill_name"
done
```

### GitHub Copilot (global)

```bash
mkdir -p ~/.copilot/skills
for skill in ~/opensite-skills/*/; do
  skill_name=$(basename "$skill")
  ln -sfn "$skill" ~/.copilot/skills/"$skill_name"
done
```

> The setup script detects Copilot by checking for `~/.copilot` or the `gh` CLI. If neither is present the section is skipped automatically.

### Repo-level (check in alongside code)

```bash
# Inside a specific repo — makes skills available only in that project
mkdir -p .agents/skills
for skill in ~/opensite-skills/*/; do
  skill_name=$(basename "$skill")
  ln -sfn "$skill" .agents/skills/"$skill_name"
done
```

---

## Codex Auto-Deepening

Codex has a built-in task that periodically analyzes work history and updates skills. Because Codex writes to `~/.codex/skills/` and your symlinks point back here, **any deepening Codex does will write directly into this git repo**. Commit and push after Codex updates a skill to propagate changes to all platforms.

Suggested workflow:

```bash
# After a Codex deepening session
cd ~/opensite-skills
git add -A
git commit -m "chore(skills): codex deepening $(date +%Y-%m-%d)"
git push

# Then re-upload changed skills to cloud platforms
./sync-perplexity.sh --changed-only
./sync-claude.sh --changed-only
```

---

## Skills Inventory

### Memory System

> **Four skills that work as a unit.** Install all four. Use `memory-recall` to start every session and `memory-write` to end it. Run `memory-consolidate` weekly.

| Skill | Role | Invoke When |
|-------|------|-------------|
| `memory` | Core store — schema, scripts, direct operations | Direct memory reads/writes/searches |
| `memory-recall` | Loads all relevant context before work begins | Start of session / "do you remember…" |
| `memory-write` | Extracts and persists session learnings | End of session / "save this" / "remember this" |
| `memory-consolidate` | Decays confidence, deduplicates, compresses old sessions | Weekly / monthly / after bulk writes |

### AI / Research

| Skill | Description |
| ------- | ------------- |
| `ai-research-workflow` | Multi-step AI research orchestration: `WorkflowBuilder`/`WorkflowStep` system, dual-model routing (Opus for deep research + web search, Sonnet for structured generation), parallel step execution, shared `MemoryStore` between steps, and `ai_tasks` persistence pattern |
| `ai-retrieval-patterns` | Retrieval architecture decision framework — when to use vector RAG, PageIndex (vectorless PDF tree-search), or precision embedding models. Covers Milvus collection design, hybrid two-stage pipelines, the `EmbeddingProvider` abstraction (BGE-M3, Qwen3), and the routing layer that ties strategies together |

### UI / Frontend

| Skill | Description |
| ------- | ------------- |
| `opensite-ui-components` | `@opensite/ui@3.x` component patterns — Semantic UI Engine, block/skin architecture, Radix UI, framer-motion, Tailwind CSS v4, and the component registry system |
| `tailwind4-shadcn` | Tailwind CSS v4 + ShadCN UI (new-york style): CSS-first configuration, CSS variable theming, v3→v4 migration patterns, and the style dashboard / tweakcn-inspired customization workflow |
| `page-speed-library` | `@page-speed/*` sub-library development: tsup bundling, peer dependency management, and the full package graph (`blocks`, `router`, `forms`, `img`, `video`, `skins`, `hooks`, `lightbox`, `pdf-viewer`, and more) |
| `semantic-ui-builder` | AI-powered site builder patterns: component registry lookups, structured-output UI generation, block selection and skin application, and the v0-clone-inspired builder interface |
| `client-side-routing-patterns` | Client-side routing with the History API — `pushState`/`replaceState`, `popstate` listeners, provider-optional hooks, SSR-safe browser API access, scroll behavior, and parameter parsing |
| `react-rendering-performance` | React 19+ rendering performance: React Compiler diagnostics, profiler-driven optimization, `useTransition` for non-blocking updates, `Activity` and `ViewTransition` components, resource preloading APIs, and when to actually reach for `useMemo`/`useCallback` |

### Rails / Backend

| Skill | Description |
| ------- | ------------- |
| `rails-query-optimization` | Advanced ActiveRecord optimization: diagnosing N+1 beyond simple `includes`, the cartesian product trap with multiple `has_many` eager loads, CTEs and lateral joins via Arel and raw SQL, reading `EXPLAIN ANALYZE` output, and counter cache patterns |
| `rails-zero-downtime-migrations` | Safe schema changes without downtime: the hot-compatibility principle, concurrent index creation, multi-step column operations, constraint validation strategies, and release-phase coordination |
| `sidekiq-job-patterns` | Production-grade Sidekiq job design: idempotency, database-level locking, transient vs permanent error classification, dead job management, and version-aware API differences across Sidekiq 6.5.x through 8.x |

### Rust / Backend

| Skill | Description |
| ------- | ------------- |
| `rust-async-patterns` | Senior-level async Rust: `Future` `Send` bound failures, Rust 2024 lifetime capture rules, task cancellation with `CancellationToken`, blocking/async boundary design, and timeout composition with Tokio |
| `rust-error-handling` | Idiomatic Rust error design: `thiserror` vs `anyhow` boundary decisions, error hierarchy design, context chain propagation, HTTP handler error mapping, and patterns that prevent error type proliferation |

### Database / Performance

| Skill | Description |
| ------- | ------------- |
| `pgvector-optimization` | pgvector performance: HNSW vs IVFFlat index selection and tuning, `ef_search` / `m` / `ef_construction` parameters, iterative scanning for filtered queries, scalar and binary quantization for memory reduction, and dimensionality compression |
| `postgres-performance-engineering` | PostgreSQL performance engineering beyond basic indexing: query plan instability, statistics staleness, `EXPLAIN ANALYZE` interpretation, GIN index pending list management, extended statistics for correlated columns, PgBouncer pooling modes, and autovacuum tuning |

### DevOps / Operations

| Skill | Description |
| ------- | ------------- |
| `agent-file-engine` | Root and nested `AGENTS.md` authoring and coverage planning — repo inventory, scope model decisions, quality bar for what earns a nested file, and templates for root and nested agent context files |
| `git-workflow` | Branch naming, Conventional Commits, PR templates, cross-repo change coordination, GitHub Actions CI patterns for Rust and Rails, hotfix process, and database migration safety checklist (manual-invoke only) |
| `automation-builder` | Browser and system automation: Playwright + real browser binary for Cloudflare-protected SPAs, session cookie injection, SPA readiness patterns, React `filechooser` upload flow, error recovery in loops, shell script safety headers, and media tool selection (ffmpeg, ImageMagick, Sharp) |

### Quality / Security

| Skill | Description |
| ------- | ------------- |
| `code-review-security` | Security-focused PR review: PHI/PII data leakage detection, authentication and authorization coverage, SQL injection scanning, secrets/credential exposure, SSRF risk in external HTTP calls, unsafe Rust code auditing, LLM output trust boundaries, and rate limiting on expensive endpoints |

---

## Claude Code–Specific Frontmatter

Some skills use Claude Code extensions (`context: fork`, `disable-model-invocation`, `user-invocable`). These fields are **unknown YAML** to Codex, Perplexity, Cursor, and Copilot — they are silently ignored. Safe to leave in place; they only activate on Claude Code.

| Skill | Claude Code behavior | Other platforms |
| ------- | --------------------- | ----------------- |
| `agent-file-engine` | Runs in forked subagent for repo analysis | Inline execution |
| `git-workflow` | Requires explicit `/git-workflow` (no auto-invoke) | Explicit-only via `agents/openai.yaml` |
| `code-review-security` | Runs in forked subagent | Inline execution |
| `postgres-performance-engineering` | Runs in forked subagent | Inline execution |

---

## Structural Standards

Every skill follows the same portable baseline:

- `SKILL.md` contains standard `description`, `compatibility`, and `metadata` fields.
- `agents/openai.yaml` provides Codex UI metadata and implicit-invocation policy.
- `references/activation.md` gives a portable activation guide plus an explicit invocation example.
- Complex skills may also ship `templates/`, `examples/`, or `scripts/` when those resources materially improve execution.

Refresh and validate the structure with:

```bash
python3 scripts/refresh_skill_support.py
python3 scripts/validate_skills.py
```

---

## Platform Conventions (Preserved Across All Tools)

These conventions emerge directly from the skills in this repo and apply regardless of which AI engine is active:

1. **Real Browser for Bot-Protected SPAs** — Use Playwright with a real Brave/Chrome binary in headed mode for any site behind Cloudflare. Headless Chromium is fingerprinted and blocked. (`automation-builder`)
2. **CSS Variables over Color Values** — Use `bg-background`, `text-foreground`, `border-border`; never `bg-white` or hardcoded hex values. (`tailwind4-shadcn`, `opensite-ui-components`)
3. **Parameterized Queries Always** — Never construct SQL via string interpolation or concatenation in any language. (`code-review-security`, `rails-query-optimization`)
4. **Measure Before Optimizing** — Run `EXPLAIN (ANALYZE, BUFFERS)` and use the React Profiler before changing a query or adding memoization. Guessing direction is wrong most of the time. (`postgres-performance-engineering`, `react-rendering-performance`)
5. **`thiserror` for Libraries, `anyhow` for Applications** — The wrong choice at a module boundary forces error type changes across every caller. (`rust-error-handling`)
6. **Session Cookies, Not Login Automation** — Inject session cookies extracted from DevTools rather than automating login flows to avoid CAPTCHAs, 2FA, and rate limits. (`automation-builder`)
7. **Hot-Compatibility for Migrations** — Every schema change must be safe to run while the old application version is still serving traffic. Deploy code before the breaking migration, not after. (`rails-zero-downtime-migrations`)

---

## Repo Structure

```
opensite-skills/
├── memory/                        ← Core memory store + scripts
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── write_memory.py
│   │   ├── search_memory.py
│   │   ├── list_memories.py
│   │   └── consolidate.py
│   └── store/                     ← gitignored — local only
│       ├── episodic/
│       ├── semantic/
│       ├── procedural/
│       └── working/
├── memory-recall/                 ← Context retrieval agent
│   └── SKILL.md
├── memory-write/                  ← Session capture agent
│   └── SKILL.md
├── memory-consolidate/            ← Maintenance agent
│   └── SKILL.md
├── ai-research-workflow/          ← Multi-step AI pipeline orchestration
├── ai-retrieval-patterns/         ← RAG, PageIndex, hybrid retrieval
├── agent-file-engine/             ← AGENTS.md authoring + coverage planning
├── automation-builder/            ← Playwright, shell, and media automation
├── client-side-routing-patterns/  ← History API, SPA routing hooks
├── code-review-security/          ← Security-focused PR review
├── git-workflow/                  ← Branch, commit, PR, CI conventions
├── opensite-ui-components/        ← @opensite/ui component patterns
├── page-speed-library/            ← @page-speed/* package development
├── pgvector-optimization/         ← pgvector HNSW/IVFFlat tuning
├── postgres-performance-engineering/ ← Query planning, vacuuming, PgBouncer
├── rails-query-optimization/      ← N+1, CTEs, EXPLAIN ANALYZE
├── rails-zero-downtime-migrations/ ← Safe schema changes on live databases
├── react-rendering-performance/   ← React 19 Compiler, Profiler, transitions
├── rust-async-patterns/           ← Tokio, Send bounds, cancellation
├── rust-error-handling/           ← thiserror/anyhow, error hierarchy design
├── semantic-ui-builder/           ← AI-powered site builder patterns
├── sidekiq-job-patterns/          ← Idempotency, locking, version-aware API
├── tailwind4-shadcn/              ← Tailwind v4 + ShadCN theming
├── <skill-name>/
│   ├── SKILL.md                   ← Main skill instructions + frontmatter
│   ├── agents/openai.yaml         ← Codex/OpenAI UI metadata
│   ├── references/activation.md  ← Portable activation + invocation guide
│   ├── templates/                 ← Optional task/output templates
│   ├── examples/                  ← Optional sample outputs or briefs
│   └── scripts/                   ← Optional helper or validation scripts
├── AGENTS.md              ← Root context (Codex, Cursor, Copilot, Windsurf, Cline)
├── CLAUDE.md              ← Root context (Claude Code only)
├── README.md
├── scripts/refresh_skill_support.py
├── scripts/validate_skills.py
├── setup.sh               ← Symlink installer (Claude Code, Codex, Copilot, Cursor)
├── sync-perplexity.sh     ← Perplexity Computer cloud sync
├── sync-claude.sh         ← Claude Desktop cloud sync
└── .env                   ← Session cookies (gitignored)
```

Any tool that reads via symlink picks up changes immediately (no reinstall needed).
Cloud platforms (Perplexity, Claude Desktop) require a re-upload after skill changes.