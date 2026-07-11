# Model Wiring — Local + Cloud

Wire AI agents to **both** cloud providers and your local engines, front them with a
LiteLLM proxy, and route tasks to the cheapest model that can do the job. Env-var
names and endpoints are **as of 2026-07 — verify.** Never keep long-lived keys in
plaintext on disk.

## 1. Cloud API keys (secure storage)

Env-var conventions:
- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Google: `GEMINI_API_KEY` / `GOOGLE_API_KEY` (or Vertex ADC +
  `GOOGLE_APPLICATION_CREDENTIALS`)
- Enterprise routing: Bedrock / Vertex / Foundry via their provider env vars.

**Base-URL overrides** repoint an agent at a proxy/gateway/compatible endpoint:
- Anthropic clients (Claude Code): `ANTHROPIC_BASE_URL`, `ANTHROPIC_AUTH_TOKEN`.
- OpenAI-compatible clients: `OPENAI_BASE_URL` / `OPENAI_API_BASE`.

**Secure storage:** do **not** put keys in shell rc or a committed `.env`. Use
**1Password `op run`** (references resolved into env at launch, masked in stdout,
never on disk) or **1Password Environments** (FIFO-backed `.env`). Alternatives:
`pass`, `gopass`, `direnv`+age, Vault, OS keychain. Example placeholder values look
like `sk-...` and `${ANTHROPIC_API_KEY}` — never commit a real key.

## 2. Local endpoints

- **Ollama** is the baseline. Serve for agents/containers:
  `export OLLAMA_HOST=0.0.0.0:11434 && ollama serve`. It exposes an
  **OpenAI-compatible** API at `http://localhost:11434/v1`, so any OpenAI-compatible
  agent (Continue, aider, OpenCode, Cline, Codex compat profiles) points there with a
  dummy key. LM Studio (`:1234/v1`), llama-server (`:8080/v1`), vLLM (`:8000/v1`),
  SGLang (`:30000/v1`), TabbyAPI (`:5000/v1`) do the same.
- **Protocol-mismatch gotcha:** Claude Code speaks the **Anthropic Messages API**;
  Ollama/LM Studio speak **OpenAI Chat Completions**. You cannot just set
  `ANTHROPIC_BASE_URL` to Ollama — you need a translation layer (LiteLLM). Note
  llama-server and LM Studio *also* expose an Anthropic-compatible endpoint directly.

## 3. LiteLLM proxy — the universal glue

Run one OpenAI/Anthropic-compatible endpoint in front of any provider (cloud +
Ollama + vLLM + llama-server) with auth, logging, budgets, spend tracking, and
**model routing/fallbacks**. Two modes: the Python SDK (`from litellm import
completion` + `Router`) and the **proxy server** (virtual keys, per-project spend,
guardrails, caching, admin UI).

```bash
pipx install 'litellm[proxy]'      # then author config.yaml + run `litellm`
```

**Feed Claude Code a local model:** run LiteLLM, name a model after a real Anthropic
model (so the client needs no changes), then point Claude Code at the proxy:
```bash
export ANTHROPIC_BASE_URL="http://localhost:4000"
export ANTHROPIC_AUTH_TOKEN="sk-litellm-key"
claude
```
(Anthropic notes it does not endorse/audit LiteLLM — it is a community tool.) A ready
config that maps an Anthropic-named alias to a local Ollama model plus real cloud
models is in [../templates/litellm-config.yaml](../templates/litellm-config.yaml).

Use LiteLLM to: (a) load-balance across several local GPUs/engines, (b) fall back
local → cloud, (c) give a team one keyed endpoint, (d) track cost/usage. Simpler
alternatives: **Claude Code Router** (solo task-based routing), **OpenRouter**
(hosted multi-provider gateway; ~5.5% credit fee, BYOK 0% markup).

## 4. Cost & model routing

- **Right-size the model per task.** Rough Anthropic tiering (as of 2026-07 —
  verify): **Opus** (~$5/$25 per Mtok) for architecture/deep reasoning/review;
  **Sonnet** for everyday coding; **Haiku** (~$1/$5, ~15× cheaper than Opus) for
  search/grep/test-running/classification/simple edits.
- **Route subagents.** In Claude Code, subagents inherit the main model unless set —
  on an Opus default, read-only helpers waste money. Assign Haiku/Sonnet via `model:`
  in frontmatter. Pattern: **Haiku triages → Sonnet builds → Opus reviews.**
- **Offload to local.** Route autocomplete + trivial transforms to Ollama
  (`qwen2.5-coder`) to cut cloud spend to zero for high-frequency low-stakes work.
- **Cut token waste.** Enable MCP tool-search/deferral (`ENABLE_TOOL_SEARCH`), keep
  `AGENTS.md`/`CLAUDE.md` lean, prune unused MCP servers, use prompt caching, and
  prefer plan mode before large edits. Subscription plans (Claude Pro/Max, ChatGPT
  Plus/Pro for Codex) can beat metered API for heavy interactive use.

## 5. Verify the wiring

```bash
# OpenAI-shaped local endpoint
curl -s http://localhost:11434/v1/models | head
# Through the LiteLLM proxy (Anthropic-shaped, for Claude Code)
curl -s http://localhost:4000/v1/models -H "Authorization: Bearer sk-litellm-key" | head
```
A test completion returning without an auth/protocol error confirms the route.
