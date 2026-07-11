# MCP Servers

Model Context Protocol (MCP) connects AI apps to external systems. This file covers
what MCP is, the essential servers for a dev box, where config lives per client, and
— most importantly — the security model. Treat **every server as untrusted code and
a prompt-injection surface.** Server names/endpoints are **as of 2026-07 — verify.**

## 1. What MCP is

An open standard (open-sourced by Anthropic, now broad cross-vendor adoption) —
"USB-C for AI." A **client** (Claude Code, ChatGPT, VS Code, Cursor, Zed, Gemini
CLI, Goose…) connects to **servers** that expose **tools**, **resources**, and
**prompts**. There is a public **MCP Registry** (`registry.modelcontextprotocol.io`)
and per-vendor directories (e.g. `claude.ai/directory`).

**Transports:**
- **stdio** — local subprocess (most dev servers; direct system access). Default when
  a JSON entry has a `command`.
- **HTTP (`streamable-http`)** — remote/hosted servers. A JSON `url` entry **must**
  set `"type": "http"` (or `sse`/`ws`) or the client treats it as stdio and fails.
- **SSE** — deprecated; prefer HTTP.

## 2. Essential servers for a dev box

Reference servers (maintained by the MCP steering group) + widely used community/vendor:

- **filesystem** — scoped file operations. Scope it to specific dirs.
- **git** — read/search/manipulate local repos.
- **github** — issues/PRs/code search/CI (official GitHub MCP server).
- **context7** (`@upstash/context7-mcp`) — up-to-date, version-correct library docs
  injected on demand; remote `https://mcp.context7.com/mcp` (API key for higher
  limits) or local via npx.
- **playwright** — drive a real browser (nav/click/snapshot/console/network) for E2E.
- **memory** — knowledge-graph persistence across sessions.
- **fetch** — web page → markdown.
- **sequential-thinking** — structured multi-step reasoning helper.
- Also common: postgres/database, sentry, cloudflare, vercel, serena (semantic code),
  and hundreds more via the registry.

## 3. Configuring servers (per client)

**Claude Code** with scopes — **Local** (`~/.claude.json`, current project only,
private), **Project** (`.mcp.json`, committed, team-shared), **User** (all projects):
```bash
claude mcp add --scope user context7 -- npx -y @upstash/context7-mcp --api-key ${CONTEXT7_API_KEY}
claude mcp add --scope project filesystem -- npx -y @modelcontextprotocol/server-filesystem ./
claude mcp add --scope project git -- npx -y mcp-server-git
claude mcp add --transport http github https://api.githubcopilot.com/mcp/
claude mcp add --scope project playwright -- npx -y @playwright/mcp
claude mcp add-json <name> '{"type":"http","url":"...","headers":{...}}'
```
Tools are referenced as `mcp__<server>__<tool>` in permission rules / `allowed-tools`
/ hooks. Other clients each have their own location (`~/.gemini/settings.json`,
per-IDE settings, `opencode.json`, `.cursor/mcp.json`, VS Code `mcp.json`) but the
server-definition shape (command/args/env, or url/type/headers) is portable.

## 4. Security (the important part)

- **Every server is untrusted code + a prompt-injection surface.** Servers that
  fetch external content (web pages, issues, emails) can smuggle instructions into
  your agent. Only connect servers you trust; read the source of stdio servers you
  run locally.
- **Least privilege.** Scope filesystem servers to specific dirs; give tokens the
  minimum scopes; avoid mixing high-privilege write tools with content-fetching
  servers in the same session (a classic injection escalation path).
- **Deny/allow rules.** In Claude Code, `permissions.deny` can block `mcp__*` (all
  MCP) or specific tools; servers can mark tools `requiresUserInteraction` to force a
  prompt even in auto modes.
- **Secrets.** MCP env/headers often carry API keys — inject via a secrets manager,
  never commit `.mcp.json` with plaintext tokens (use env-var interpolation like
  `${GITHUB_TOKEN}`). See secrets guidance in [ai-coding-agents.md](ai-coding-agents.md).
- **Context/token bloat.** Many servers add lots of tools; use on-demand tool loading
  (e.g. `ENABLE_TOOL_SEARCH` in Claude Code) and prune servers you do not use.

## 5. Checklist before adding a server

1. Do I trust the publisher / have I read the source?
2. Is it scoped to the minimum filesystem paths and token permissions?
3. Am I keeping content-fetching servers isolated from high-privilege write tools?
4. Are all secrets injected from a manager (no plaintext in committed config)?
5. Is the correct scope chosen (Local for private, Project for team-shared)?
6. For HTTP servers, did I set `"type": "http"` explicitly?
