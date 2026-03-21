# OpenSite AI Coding Agent Skills + Multi Agent Support

## Single source of truth for the comprehensive and continually updating AI coding agent skills

The skills range from front end design specialization, Rust/Ruby/Node backend capabilities, along with utility commands and features that have been fine tuned in the development of the [OpenSite AI Platform](https://opensite.ai). And because the idea of trying to keep a constantly growing list of coding agents to all have nearly identical set of skills in sync *(especially considering that we run scheduled `deepening` tasks to continually refine the set of skills)* sounded like a special spot in hell I don't believe I did anything to deserve... we built out a full set of scripts that will let you keep a single repo of skills for all coding agents.

These skills follow the [Agent Skills open standard](https://agentskills.io) and are compatible with:

| Platform | Skill Location | Load method |
| ---------- | --------------- | ------------- |
| **Claude Code** | `~/.claude/skills/` (global) or `.claude/skills/` (project) | Automatic + `/skill-name` |
| **Claude Desktop** | Cloud upload — `claude.ai/customize/skills` | Automatic trigger |
| **Codex** | `~/.codex/skills/` (global) or `.agents/skills/` (repo) | Automatic + `$skill-name` |
| **Perplexity Computer** | Cloud upload — `perplexity.ai/account/org/skills` | Automatic trigger |
| **Cursor / Copilot** | `.cursor/skills/` or `.github/skills/` per-repo | Via `/` commands |

> **One repo, zero copying.** Set this up once with the platform setup script and all tools read from the same directory via symlinks. Update a skill once — all tools see the change instantly.

---

## Quick Setup

> For local platforms: Claude Code, Codex, and Cursor. Dedicated scripts for cloud platforms (Perplexity, Claude Desktop) below.

```bash
# 1. Clone to a stable location
git clone git@github.com:Toastability/opensite-skills.git ~/opensite-skills
cd ~/opensite-skills

# 2. Run the setup script
./setup.sh
```

The setup script creates symlinks from each platform's skills directory to this repo — no file copying.

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
(the org settings page has a direct "Upload skill" button — no dropdown required)

```bash
./sync-perplexity.sh                   # sync all skills
./sync-perplexity.sh --changed-only    # only git-modified skills since last commit
./sync-perplexity.sh octane-rust-axum  # one specific skill by name
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
./sync-claude.sh                   # sync all skills
./sync-claude.sh --changed-only    # only git-modified skills since last commit
./sync-claude.sh octane-rust-axum  # one specific skill by name
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

### Octane — Rust + Axum

| Skill | Description |
| ------- | ------------- |
| `octane-rust-axum` | Axum 0.8 handler/route/service patterns |
| `octane-soc2-hipaa` | SOC2 + HIPAA compliance — `AuditedLlmProvider`, PHI rules |
| `octane-llm-engine` | Self-hosted LLM engine (vLLM, Llama 3.3, traits, routing) |
| `octane-embedding-pipeline` | BGE-M3, Qwen3-Embedding, Milvus vector search |

### AI / Research

| Skill | Description |
| ------- | ------------- |
| `ai-research-workflow` | Multi-step research orchestration with Opus 4.6 |

### UI / Frontend

| Skill | Description |
| ------- | ------------- |
| `opensite-ui-components` | `@opensite/ui@3.x` component patterns |
| `tailwind4-shadcn` | Tailwind v4 + ShadCN (new-york style) |
| `page-speed-library` | `@page-speed/*` library development |
| `semantic-ui-builder` | AI-powered site builder patterns |

### Rails / Backend

| Skill | Description |
| ------- | ------------- |
| `rails-api-patterns` | `toastability-service` + `dashtrack-ai` conventions |

### DevOps / Operations

| Skill | Description |
| ------- | ------------- |
| `agent-file-engine` | Root + nested `AGENTS.md` authoring and coverage planning |
| `deploy-fly-io` | Fly.io + Tigris deployment (manual-invoke only) |
| `sentry-monitoring` | Error tracking across all services |
| `git-workflow` | Branch, commit, PR conventions (manual-invoke only) |

### Quality / Security

| Skill | Description |
| ------- | ------------- |
| `code-review-security` | Security-focused PR review (forked subagent) |
| `gpu-workers-python` | RunPod GPU worker patterns |

---

## Claude Code–Specific Frontmatter

Some skills use Claude Code extensions (`context: fork`, `disable-model-invocation`, `user-invocable`). These fields are **unknown YAML** to Codex, Perplexity, and Cursor — they are silently ignored. Safe to leave in place; they only activate on Claude Code.

| Skill | Claude Code behavior | Other platforms |
| ------- | --------------------- | ----------------- |
| `agent-file-engine` | Runs in forked subagent for repo analysis | Inline execution |
| `deploy-fly-io` | Requires explicit `/deploy-fly-io` (no auto-invoke) | Explicit-only in Codex via `agents/openai.yaml` |
| `git-workflow` | Requires explicit `/git-workflow` | Explicit-only in Codex via `agents/openai.yaml` |
| `code-review-security` | Runs in forked subagent | Inline execution |
| `postgres-performance-engineering` | Runs in forked subagent | Inline execution |
| `sentry-monitoring` | Background only, not user-facing | Standard skill |

---

## Structural Standards

Every skill now follows the same portable baseline:

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

1. **PHI Safety** — No user content in logs. Always hash prompts before audit logging.
2. **Typed State in Axum** — `State<Arc<HandlerState>>`, never `Extension<Pool>`
3. **CSS Variables** — `bg-background`, `text-foreground`, never `bg-white`
4. **SOC2 Audit Trail** — Every LLM call wrapped in `AuditedLlmProvider`
5. **Schema Migrations** — Only in `toastability-service`, synced to all apps
6. **Fly.io Private Network** — `{app}.internal:{port}` addresses throughout
7. **Tigris S3** — `https://fly.storage.tigris.dev` endpoint

---

## Repo Structure

```
opensite-skills/
├── <skill-name>/
│   ├── SKILL.md                 ← Main skill instructions + frontmatter
│   ├── agents/openai.yaml       ← Codex/OpenAI UI metadata
│   ├── references/activation.md ← Portable activation + invocation guide
│   ├── templates/               ← Optional task/output templates
│   ├── examples/                ← Optional sample outputs or briefs
│   └── scripts/                 ← Optional helper or validation scripts
├── CLAUDE.md             ← Root context (Claude Code only)
├── README.md
├── scripts/refresh_skill_support.py
├── scripts/validate_skills.py
├── setup.sh              ← Symlink installer (Claude Code, Codex, Cursor)
├── sync-perplexity.sh    ← Perplexity Computer cloud sync
├── sync-claude.sh        ← Claude Desktop cloud sync
└── .env                  ← Session cookies (gitignored)
```

Any tool that reads via symlink picks up changes immediately (no reinstall needed).
Cloud platforms (Perplexity, Claude Desktop) require a re-upload after skill changes.
