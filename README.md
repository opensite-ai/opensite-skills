# OpenSite AI Coding Agent Skills + Multi Agent Support

## Single source of truth for the comprehensive and continually updating AI coding agent skills

The skills range from front end design specialization, Rust/Ruby/Node backend capabilities, along with utility commands and features that have been fine tuned in the development of the [OpenSite AI Platform](https://opensite.ai). And because the idea of trying to keep a constantly growing list of coding agents to all have nearly identical set of skills in sync *(especially considering that we run scheduled `deepening` tasks to continually refine the set of skills)* sounded like a special spot in hell I don't believe I did anything to deserve... we built out a full set of scripts that will let you keep a single repo of skills for all coding agents.

These skills follow the [Agent Skills open standard](https://agentskills.io) and are compatible with:

| Platform | Skill Location | Load method |
| ---------- | --------------- | ------------- |
| **Claude Code** | `~/.claude/skills/` (global) or `.claude/skills/` (project) | Automatic + `/skill-name` |
| **Codex** | `~/.codex/skills/` (global) or `.agents/skills/` (repo) | Automatic + `$skill-name` |
| **Perplexity Computer** | Cloud upload — Skills page → Upload a Skill | Automatic trigger |
| **Cursor / Copilot** | `.cursor/skills/` or `.github/skills/` per-repo | Via `/` commands |

> **One repo, zero copying.** Set this up once with the platform setup script and all tools read from the same directory via symlinks. Update a skill once — all tools see the change instantly.

---

## Quick Setup

> For primary platforms: Claude Code, Codex, and Cursor. Dedicated script for Perplexity Computer in the `Manual Setup` section below.

```bash
# 1. Clone to a stable location
git clone git@github.com:Toastability/opensite-skills.git ~/opensite-skills
cd ~/opensite-skills

# 2. Run the setup script
./setup.sh
```

The setup script creates symlinks from each platform's skills directory to this repo — no file copying.

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

### Perplexity Computer

Perplexity uses cloud-hosted skills (no local filesystem). Run the upload script to sync:

```bash
./sync-perplexity.sh   # reads PERPLEXITY_API_KEY from env or .env file
```

Or upload manually: go to **Skills → Create Skill → Upload a Skill**, then drag in any `SKILL.md` or a `.zip` of the skill folder. Max 10 MB per upload.

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

# Then re-upload changed skills to Perplexity
./sync-perplexity.sh --changed-only
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
| `deploy-fly-io` | Requires explicit `/deploy-fly-io` (no auto-invoke) | Auto-invoke eligible |
| `git-workflow` | Requires explicit `/git-workflow` | Auto-invoke eligible |
| `code-review-security` | Runs in forked subagent | Inline execution |
| `sentry-monitoring` | Background only, not user-facing | Standard skill |

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

## Updating Skills

```bash
opensite-skills/
├── <skill-name>/
│   ├── SKILL.md          ← Edit this to update a skill
│   └── *.md              ← Supporting reference docs
├── CLAUDE.md             ← Root context (Claude Code only)
├── README.md
├── setup.sh              ← Symlink installer
└── sync-perplexity.sh    ← Perplexity upload helper
```

Any tool that reads via symlink picks up changes immediately (no reinstall needed).
Perplexity requires a re-upload since it stores skills in the cloud.
