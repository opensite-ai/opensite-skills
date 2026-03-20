# OpenSite AI Coding Agent Skills + Multi Agent Support

You are working in the OpenSite / Toastability codebase. This CLAUDE.md is the root context file that applies to all sessions in this repository set.

## Organization Overview

| Org | Focus |
|-----|-------|
| `opensite-ai` | Semantic UI Engine libraries (`@opensite/ui`, `@page-speed/*`) |
| `Toastability` | Platform applications (`octane`, `toastability-service`, `app`, `dashtrack-ai`) |

## Primary Repositories

### Core Platform
- **`Toastability/octane`** — Rust+Axum AI API. The central service. All AI tasks, embeddings, semantic UI, SEO analysis run here. **Rust 1.91+, Axum 0.8, Fly.io.**
- **`Toastability/toastability-service`** — Rails 6.1 primary API. Restaurant management platform. Owns the PostgreSQL schema. **Ruby 3.3, Heroku.**
- **`Toastability/app`** — Next.js 16 CMS frontend (dashtrack-cms). The operator-facing dashboard. **React 19, Tailwind v4.**
- **`Toastability/dashtrack-ai`** — Rails 8.0.3 MCP connector for Claude. Function-based API. **Shares DB with toastability-service.**

### UI Libraries
- **`opensite-ai/opensite-ui`** — `@opensite/ui@3.x` — foundational component library (TSup + TW4 + Radix)
- **`opensite-ai/ui-library`** — Next.js showcase for the component library
- **`opensite-ai/page-speed-*`** — Sub-libraries (img, video, forms, router, skins, hooks, etc.)

## Technology Stack

### Octane (Rust)
- Axum 0.8, Tokio async runtime
- deadpool-postgres + tokio-postgres + sqlx
- Anthropic API (dual-model: Opus 4.6 research, Sonnet 4.6 generation)
- Voyage AI embeddings (migrating to self-hosted BGE-M3 + Qwen3-Embedding-8B)
- ONNX Runtime (U2-Net, Xception, etc.)
- Tigris S3 (object storage on Fly.io)
- Sentry 0.46.1 (structured JSON tracing)

### Rails Services
- Rails 6.1 (toastability-service) + Rails 8.0.3 (dashtrack-ai)
- Ruby 3.3, Sidekiq + Redis, PostgreSQL
- Heroku deployment, RSpec tests

### Frontend
- Next.js 16, React 19, TypeScript 5
- Tailwind CSS v4 (CSS-first config)
- ShadCN UI (new-york style), Radix UI primitives
- CVA (class-variance-authority), tailwind-merge
- Vercel deployment

## Critical Rules

1. **No PHI in logs** — Never log raw prompts, responses, emails, phone numbers, or any user-submitted content in production code. Hash prompt content before logging.

2. **Audit every LLM call** — Wrap all LLM provider calls with `AuditedLlmProvider` in Octane. This is a HIPAA requirement.

3. **No migrations in dashtrack-ai** — Only `toastability-service` owns the database schema. `dashtrack-ai` syncs schema with `bundle exec rake toast:schema:sync`.

4. **CSS variables, not hardcoded colors** — All UI components use CSS variable tokens (`bg-background`, `text-foreground`, etc.), never `bg-white`, `text-gray-900`.

5. **AppError, not unwrap** — All Octane handlers return `Result<Json<T>, AppError>`. Never use `.unwrap()` or `.expect()` in handler code.

6. **Typed state, not raw Extension** — Use typed state structs in Axum handlers, not `Extension<Pool>`.

## Available Skills

These skills are available in `.claude/skills/`. Load them with `/skill-name` or let Claude load them automatically:

| Skill | When to Use |
|-------|-------------|
| `octane-rust-axum` | Adding routes, handlers, services in Octane |
| `octane-soc2-hipaa` | Compliance, audit logging, PHI handling |
| `octane-llm-engine` | Building the self-hosted LLM service (vLLM, Llama, traits) |
| `octane-embedding-pipeline` | BGE-M3, Qwen3, Milvus vector search |
| `opensite-ui-components` | Component library development |
| `tailwind4-shadcn` | Tailwind v4 config, ShadCN customization, theming |
| `page-speed-library` | @page-speed/* library development |
| `semantic-ui-builder` | AI-powered site builder (Octane + CMS) |
| `rails-api-patterns` | toastability-service + dashtrack-ai development |
| `deploy-fly-io` | Fly.io deployments, Tigris, GPU machines |
| `sentry-monitoring` | Error tracking across all services |
| `git-workflow` | Branch naming, commits, PRs, CI |
| `ai-research-workflow` | Brand guide, market analysis, multi-step AI workflows |
| `code-review-security` | Security-focused PR reviews |
| `gpu-workers-python` | RunPod GPU worker tasks |

## Model Routing Guide

| Task | Model | Why |
|------|-------|-----|
| Deep research (brand guide, market analysis) | Opus 4.6 | 1M context, novel reasoning, web search |
| Report generation, structured output | Sonnet 4.6 | 98% Opus performance, 5x cheaper |
| Security audits, architecture reviews | Opus 4.6 | High-stakes, deep reasoning |
| Standard coding (bug fixes, features) | Sonnet 4.6 | Near-parity performance |
| Self-hosted inference (Phase 1+) | Llama 3.3 70B | SOC2/HIPAA compliant, $0.002-0.005/1K |

## Cloud Skill Sync

Skills in this repo are the source of truth. Claude Code and Codex read them via symlinks (changes are instant). Cloud platforms require a re-upload after edits:

```bash
./sync-perplexity.sh    # Perplexity Computer — perplexity.ai/account/org/skills
./sync-claude.sh        # Claude Desktop     — claude.ai/customize/skills
```

Both scripts open a **visible Brave browser window** and automate the upload UI. Credentials live in `.env` (gitignored):

```
PERPLEXITY_SESSION_COOKIE=...   # from perplexity.ai cookies: __Secure-next-auth.session-token
CLAUDE_SESSION_COOKIE=...       # from claude.ai cookies: sessionKey
```

**Important implementation notes (do not regress):**
- Both scripts use the real Brave binary (`/Applications/Brave Browser.app`) in headed (visible window) mode — Playwright's bundled headless Chromium is trivially detected and blocked by Cloudflare on both sites
- File upload uses Playwright's `filechooser` event interception after clicking the upload zone — directly setting `input.files` via the DOM does not trigger React's `onChange` and silently fails
- Both scripts create a fresh browser context (not the user's existing Brave profile) and inject only the session cookie

**Update strategies differ between platforms:**
- **Perplexity** (`sync-perplexity.sh`): searches the skill list first; if found, opens the skill's `⋮` (kebab) menu and clicks the update option; if not found, clicks the top-level "Upload skill" button. Drop-zone element is a `div[role="button"]` with text "Drag your file here or click to upload".
- **Claude** (`sync-claude.sh`): always runs the identical "new skill" flow for every skill (`+` button → "Upload a skill" dropdown item); if the skill already exists Claude automatically shows a "Replace [name] skill?" confirmation dialog — the script clicks "Upload and replace". No search or ⋮ menu needed. Drop-zone element is a `<button>` with text "Drag and drop or click to upload".
