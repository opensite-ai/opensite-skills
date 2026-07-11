# AI Coding Agents & CLIs

Install, authenticate, and configure terminal AI coding agents and editor
integrations on Linux, then sandbox them and run several in parallel. All install
commands and flags are **as of 2026-07 — verify** against official docs (this space
changes weekly). Do **not** run agents in unattended/YOLO mode outside a sandbox.

## 1. Recommended core stack

Install all three — they are complementary and share the `AGENTS.md` convention:

1. **Claude Code** (Anthropic) — primary agent. Best-in-class agentic editing,
   native OS-level Bash sandbox, subagents, worktrees, hooks, plugins, skills,
   first-class MCP.
2. **OpenAI Codex CLI** — secondary. Rust binary, strong OS-enforced sandbox
   (landlock/seccomp on Linux), ChatGPT-plan or API auth; good second opinion from a
   different model family.
3. **aider** or **OpenCode** — the model-agnostic wildcard. aider for git-native
   pair programming and trivial local-model wiring (LiteLLM under the hood);
   OpenCode for a polished provider-agnostic TUI.

## 2. Terminal agents — install, auth, config

### Claude Code
```bash
curl -fsSL https://claude.ai/install.sh | bash        # native installer (self-updating)
# or: npm install -g @anthropic-ai/claude-code         # needs Node 18+; DO NOT sudo
```
Auth: run `claude` → browser OAuth (Pro/Max/Team) or Console API key, or cloud
providers (Bedrock/Vertex/Foundry) via env vars. In SSH/containers paste the login
code at the prompt. Config scopes (priority Managed > CLI > Local > Project > User):
`~/.claude/settings.json` + `~/.claude/CLAUDE.md`; `.claude/settings.json` +
`CLAUDE.md` (committed); `.claude/settings.local.json` (gitignored). Headless:
`claude -p "<prompt>" --output-format json|stream-json`; official
`anthropics/claude-code-action` GitHub Action.

### OpenAI Codex CLI
```bash
curl -fsSL https://chatgpt.com/codex/install.sh | sh   # or npm i -g @openai/codex / brew --cask codex
```
Auth: `codex` → Sign in with ChatGPT, or API key. Config: `~/.codex/config.toml`
(+ `~/.codex/AGENTS.md`). Key knobs: `approval_policy`
(`untrusted|on-request|never`), `sandbox_mode` (`read-only|workspace-write|danger-full-access`).
`--full-auto` = on-request + workspace-write. Headless: `codex exec "<prompt>"`.

### aider
```bash
python -m pip install aider-install && aider-install   # or: curl -LsSf https://aider.chat/install.sh | sh
```
Models: `aider --model sonnet --api-key anthropic=<key>`. Local (Ollama):
`export OLLAMA_API_BASE=http://127.0.0.1:11434` then
`aider --model ollama_chat/qwen2.5-coder:14b` (use the **`ollama_chat/`** prefix).
Set `num_ctx: 32768` in `.aider.model.settings.yml` — Ollama's 2048 default silently
truncates. Config: `.aider.conf.yml`, `CONVENTIONS.md` (read-only guidance).

### OpenCode & Gemini CLI
```bash
curl -fsSL https://opencode.ai/install | bash          # OpenCode (verify canonical repo/org)
npm install -g @google/gemini-cli                       # Gemini CLI (Apache-2.0, generous free tier)
```
OpenCode config: `opencode.json` + `AGENTS.md`. Gemini CLI auth: Google OAuth,
`GEMINI_API_KEY`/`GOOGLE_API_KEY`, or Vertex ADC; config `~/.gemini/settings.json`
+ `GEMINI.md`. Others in the landscape (most honor `AGENTS.md`): Cline, Goose, Amp,
Crush, Droid, Warp.

## 3. Editor integrations

- **Zed** — fastest (Rust), native Agent Panel, parallel agent threads, Edit
  Prediction, and **ACP** to run Claude Code/Codex/OpenCode inside the GUI.
  `curl -f https://zed.dev/install.sh | sh` (needs a Vulkan driver, NVIDIA ≥525).
- **VS Code + Copilot (agent mode, GA)** with MCP; or **Continue.dev** (open source,
  Ollama first-class, per-role models: `qwen2.5-coder:1.5b` autocomplete,
  `:7b`/`:32b` chat/edit; config `~/.continue/config.yaml`).
- **Cursor** — fully supported on Linux (`.deb` + AppImage from `cursor.com/download`).
- **Neovim** — `avante.nvim` (Cursor-like diff review), `codecompanion.nvim` (in-buffer
  Q&A), `copilot.lua` (inline completion).

## 4. Sandboxing & safety on a dev box

- **Permission modes.** Claude Code: `default` → `acceptEdits` → `plan` (read-only)
  → `bypassPermissions`; `permissions.allow/ask/deny` by tool+arg glob, e.g.
  `deny: ["Read(./.env)", "Read(./secrets/**)", "Bash(curl *)", "WebFetch"]`.
  Codex: `approval_policy` × `sandbox_mode` matrix (default `workspace-write`).
- **OS-level sandbox.** Claude Code sandboxed Bash (Linux/WSL2 via
  landlock/seccomp/namespaces): writes limited to the working dir + tmp; network
  deny-by-default with per-domain approval (`sandbox.enabled`,
  `filesystem.allowWrite/denyWrite`, `network.allowedDomains`,
  `allowUnsandboxedCommands:false`). Codex uses landlock/seccomp; `danger-full-access`
  disables it.
- **Containers/VMs.** Run YOLO/`--full-auto` agents inside a devcontainer or
  disposable Docker/Podman container with the repo mounted and **no host
  credentials**. Never give an unsandboxed agent your host shell + real secrets.
- **Git worktrees for parallel agents.** Each agent gets its own dir/branch:
  `claude --worktree <name>` (or `isolation: worktree` on a subagent). Pair with
  port isolation and DB branching. Use `.worktreeinclude` to copy gitignored files.
- **Guard destructive commands.** Deny/guard `rm -rf`, `git push --force`,
  `git reset --hard`, `docker`, package publishes; require approval for network/`curl`;
  add PreToolUse hooks to block dangerous patterns.

## 5. Secrets hygiene

Never commit keys or keep long-lived keys in shell rc / committed `.env`. Inject at
runtime with **1Password `op run`** (references resolved into env, masked in stdout,
never on disk) or **1Password Environments** (FIFO-backed `.env`). Alternatives:
`pass`, `gopass`, `direnv`+age, Vault, OS keychain. Keep secrets out of
agent-readable paths (`deny Read(./.env)`); rotate keys; scope tokens minimally.
See `linux-dev-workstation`'s security-hardening reference for the full secrets story.

## 6. AGENTS.md convention & productivity

- **`AGENTS.md`** is the cross-tool standard (Codex, Gemini CLI, aider, Goose,
  OpenCode, Zed, Warp, Cursor, VS Code…). Put build/test commands, conventions, and
  guidance there. **`CLAUDE.md`** is Claude Code's native memory file — many teams
  **symlink `CLAUDE.md` → `AGENTS.md`** for one source of truth (`ln -s AGENTS.md
  CLAUDE.md`). Layer: global (`~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`) + project
  root + nested per-subsystem files. Start from the template in
  `../templates/AGENTS.md`.
- **Manage the config with a dotfiles repo** (chezmoi/stow), symlinking `~/.claude/`,
  `~/.codex/`, `~/.gemini/`, `~/.continue/`, `~/.aider.conf.yml`, and MCP config;
  gitignore `settings.local.json`, `.env`, `~/.claude.json`.
- **Parallelism:** worktrees + a multiplexer (tmux/zellij) or Zed/Warp split panes —
  implement with one agent while another model reviews the diff (cheap quality boost).
- **Cost routing:** *Haiku triages → Sonnet builds → Opus reviews.* Assign cheap
  models to read-only subagents (`model:` in frontmatter); offload autocomplete +
  trivial transforms to a local Ollama model. See model-wiring.md for the proxy layer.

For MCP server setup and security, see [mcp-servers.md](mcp-servers.md). For wiring
agents to local/cloud models, see [model-wiring.md](model-wiring.md).
