---
name: context-management
description: >
  Context virtualization skill for extending effective context window across all
  AI coding agents. Provides SQLite FTS5 indexing of large tool outputs, BM25
  search for targeted snippet retrieval, deterministic output compression, and
  session checkpointing that survives context compaction. Use this skill when
  working in long sessions, when tool outputs are large (logs, diffs, snapshots),
  or when resuming after compaction. Essential for Codex CLI and other agents
  that lack hook-based automatic output interception.
version: 1.1.0
allowed-tools: "Read Write Bash Glob Grep Edit"
compatibility: >
  Works with any AI coding agent. Designed primarily for Codex CLI (which lacks
  hooks), but equally useful in Claude Code, Cursor, Windsurf, and Cline sessions.
  Requires Python 3.8+ (no pip dependencies). SQLite FTS5 is included in Python's
  bundled sqlite3 module on all major platforms.
metadata:
  opensite-category: infrastructure
  opensite-scope: cross-platform
  opensite-visibility: public
---

# Context Management Skill

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Scripts: `scripts/ctx_index.py`, `scripts/ctx_search.py`, `scripts/ctx_compress.py`, `scripts/ctx_checkpoint.py`

## Task Focus for $ARGUMENTS
When this skill is invoked explicitly, treat `$ARGUMENTS` as the primary scope:
a project directory, a tool output type to manage, or a checkpoint operation.

---

## Problem Statement

Large tool outputs (file reads, git diffs, test runs, Playwright snapshots, log dumps)
burn through the context window rapidly. Agents with hook support (Claude Code) can
intercept these automatically. Agents without hooks (Codex CLI) cannot.

This skill provides the same "context virtualization" as a portable, agent-driven
workflow: the agent invokes these tools explicitly instead of hooks doing it implicitly.

## Architecture

```
┌───────────────────────────────────────────────────┐
│  Agent Session                                     │
│                                                    │
│  1. LARGE OUTPUT generated (file read, test, log)  │
│     │                                              │
│     ▼                                              │
│  2. ctx_index.py — store full output in FTS5 DB    │
│     │                                              │
│     ▼                                              │
│  3. ctx_compress.py — return N-line summary to     │
│     agent context (full data stays in DB)          │
│     │                                              │
│     ▼                                              │
│  4. ctx_search.py — later, retrieve specific       │
│     snippets via BM25 keyword search               │
│                                                    │
│  ────────── compaction boundary ──────────          │
│                                                    │
│  5. ctx_checkpoint.py — save session state before  │
│     compaction; reload after                       │
└───────────────────────────────────────────────────┘
```

## Storage Layout

All data is stored under `.ctx/` in the project root (gitignore this directory):

```
.ctx/
├── context.db          ← SQLite FTS5 database (indexed outputs)
├── checkpoint.md       ← Latest session checkpoint
└── checkpoints/        ← Historical checkpoints
    └── YYYY-MM-DD-HHMMSS.md
```

## Core Scripts

All scripts live in `scripts/` relative to this SKILL.md. They use
`Path(__file__).resolve()` for portable path resolution. All are Python 3.8+
with zero external dependencies.

> **Path Resolution**: The scripts can be invoked with relative paths (`scripts/ctx_index.py`)
> when run from the skill's installation directory, or with absolute paths when run from
> elsewhere. The `scripts/` directory is in the same location as this SKILL.md file.

### 1. ctx_index.py — Index Content into FTS5

Index large outputs so they stay out of context but remain searchable.

```bash
# Index from stdin (pipe a command's output)
cat large_file.rs | python scripts/ctx_index.py \
  --source "file:src/handlers/mod.rs" \
  --project /path/to/project

# Index from a file
python scripts/ctx_index.py \
  --source "git:diff-main" \
  --file /tmp/git_diff_output.txt \
  --project /path/to/project

# Index inline content
python scripts/ctx_index.py \
  --source "test:cargo-test" \
  --content "$(cargo test 2>&1)" \
  --project /path/to/project

# Index with tags for filtering
python scripts/ctx_index.py \
  --source "log:fly-deploy" \
  --tags "deploy,fly,production" \
  --project /path/to/project < deploy.log
```

**What it does:**
- Creates `.ctx/context.db` if it doesn't exist
- Chunks content by markdown headings (preserving code blocks intact)
- Inserts chunks into an FTS5 virtual table with BM25 ranking
- Returns a brief confirmation with chunk count and total size

### 2. ctx_search.py — Query the FTS5 Index

Retrieve targeted snippets instead of re-reading entire files.

```bash
# Basic keyword search
python scripts/ctx_search.py \
  --query "error handling AppError" \
  --project /path/to/project

# Search with source filter
python scripts/ctx_search.py \
  --query "middleware tower" \
  --source "file:src/" \
  --project /path/to/project

# Search with tag filter and limit
python scripts/ctx_search.py \
  --query "deploy timeout" \
  --tags "production" \
  --limit 5 \
  --project /path/to/project

# List all indexed sources
python scripts/ctx_search.py \
  --list-sources \
  --project /path/to/project

# Show DB stats
python scripts/ctx_search.py \
  --stats \
  --project /path/to/project
```

**What it does:**
- Queries the FTS5 virtual table using SQLite's MATCH syntax with BM25 ranking
- Returns ranked snippets with source attribution and relevance scores
- Supports filtering by source prefix and tags
- Returns compact results that fit in context without bloat

### 3. ctx_compress.py — Deterministic Output Compression

Reduce large outputs to a fixed line budget before they enter context.

```bash
# Compress stdin to 50 lines (default)
cat huge_log.txt | python scripts/ctx_compress.py

# Compress to specific line budget
git diff HEAD~5 | python scripts/ctx_compress.py --lines 30

# Compress and index simultaneously (recommended workflow)
cargo test 2>&1 | python scripts/ctx_compress.py \
  --lines 40 \
  --index \
  --source "test:cargo-test" \
  --project /path/to/project

# Compress a file
python scripts/ctx_compress.py \
  --file /tmp/large_output.txt \
  --lines 60
```

**What it does:**
- Reads full input, extracts a deterministic summary within the line budget
- Prioritizes: errors/warnings first, then structure (headings/signatures), then content
- Appends a `[compressed: N/M lines (~X → ~Y tokens), full content indexed as {source}]` footer
- With `--index`, also stores the full uncompressed content in FTS5

### 4. ctx_checkpoint.py — Session State Persistence

Save and restore session state across Codex compaction boundaries.

```bash
# Save a checkpoint
python scripts/ctx_checkpoint.py save \
  --project /path/to/project \
  --task "Implementing OAuth2 flow for customer-sites" \
  --completed "Added OAuth routes, Created token model" \
  --in-progress "Writing token refresh middleware" \
  --next-steps "Add tests, Update AGENTS.md" \
  --decisions "Using tower middleware for auth, JWT with RS256" \
  --context "Branch: feature/oauth2, Tests passing except refresh"

# Load the latest checkpoint
python scripts/ctx_checkpoint.py load \
  --project /path/to/project

# Load checkpoint as JSON (for programmatic use)
python scripts/ctx_checkpoint.py load \
  --project /path/to/project \
  --json

# List all checkpoints
python scripts/ctx_checkpoint.py list \
  --project /path/to/project

# Save raw markdown (for agents that generate their own format)
python scripts/ctx_checkpoint.py save-raw \
  --project /path/to/project < custom_checkpoint.md
```

**What it does:**
- Writes a structured markdown checkpoint to `.ctx/checkpoint.md`
- Archives previous checkpoints with timestamps
- On load, returns the checkpoint content for context injection
- Designed to be called before compaction and after resuming
- Auto-captures git branch and last commit for additional context
- `save-raw` subcommand allows saving arbitrary markdown content

---

## Recommended Workflows

### Workflow A: Large Output Routing (Primary Use Case)

When a command will produce large output, route it through compress+index:

```bash
# Instead of raw: cargo test 2>&1
# Do this:
cargo test 2>&1 | python scripts/ctx_compress.py \
  --lines 40 --index --source "test:cargo-test" --project .

# Later, find specific test failures:
python scripts/ctx_search.py \
  --query "FAILED assertion" --project .
```

### Workflow B: File Reading with Indexing

When reading large files, index them and work from search:

```bash
# Index a large file
python scripts/ctx_index.py \
  --source "file:src/handlers/mod.rs" \
  --file src/handlers/mod.rs --project .

# Search for specific content
python scripts/ctx_search.py \
  --query "fn handle_request" --project .
```

### Workflow C: Compaction Survival

Before context compaction, checkpoint your state:

```bash
# Save state
python scripts/ctx_checkpoint.py save \
  --project . \
  --task "Current task description" \
  --completed "Done items" \
  --in-progress "Current work" \
  --next-steps "What to do next"

# After compaction, reload
python scripts/ctx_checkpoint.py load --project .
```

### Workflow D: Session Start (combine with memory-recall)

At session start, load both memory context and any existing checkpoints:

```bash
# Load checkpoint if exists
python scripts/ctx_checkpoint.py load --project .

# Check what's been indexed
python scripts/ctx_search.py --stats --project .
```

---

## Agent Routing Rules

When this skill is active, follow these routing rules:

### ALWAYS compress+index when:
- Running test suites (`cargo test`, `rspec`, `jest`, `pytest`)
- Reading git diffs larger than 50 lines
- Reading log files or deployment output
- Reading files larger than 200 lines
- Running linters with many warnings/errors

> **Note**: For files larger than ~50MB, consider pre-filtering with standard Unix tools (`head`, `grep`, `awk`) before piping to `ctx_compress.py` to avoid high memory usage.

### ALWAYS checkpoint when:
- You've completed a significant milestone
- Before the session feels long (proactively, every ~15 tool calls)
- When the user says "save state" or "checkpoint"
- Before switching to a different area of the codebase

### ALWAYS search before re-reading:
- If you've already indexed a file, search instead of re-reading it
- Use targeted queries to get only the relevant snippets

---

## Integration with Memory System

This skill complements (does not replace) the memory skills:

| System | Scope | Persistence | Purpose |
|--------|-------|-------------|---------|
| **context-management** | Current session | Project-local `.ctx/` | Keep large outputs out of context window |
| **memory** | Cross-session | Repo-local `memory/store/` | Long-term knowledge persistence |

**Recommended combined workflow:**
1. Session start: `/memory-recall` + `ctx_checkpoint.py load`
2. During session: `ctx_compress.py` + `ctx_index.py` for large outputs
3. Session end: `ctx_checkpoint.py save` + `/memory-write`

---

## .gitignore Entry

The skill automatically adds `.ctx/` to your project's `.gitignore` on first run.
If you need to add it manually:

```
# Context management data (session-local, not committed)
.ctx/
```

---

## Platform Compatibility Notes

### FTS5 vs FTS4 (BM25 Ranking)

This skill uses SQLite FTS5 for full-text search with BM25 relevance ranking.
On most platforms (macOS, Windows, standard Linux distributions), FTS5 is
available by default in Python's bundled sqlite3 module.

**If FTS5 is unavailable** (some Alpine-based Docker images, older Linux distros),
the skill automatically falls back to FTS4. In FTS4 mode:

- Search still works, but results are returned in insertion order (no BM25 ranking)
- The `rank` field in search results will show `n/a`
- All other features (indexing, compression, checkpointing) work normally

To check if you have FTS5, run:
```bash
python -c "import sqlite3; print('FTS5 available' if sqlite3.sqlite_version_info >= (3, 9, 0) else 'FTS4 fallback')"
```

### Session Isolation (Concurrent Agents)

All agents working in the same project directory share the same `.ctx/context.db`.
SQLite WAL mode handles concurrent reads/writes safely for most use cases.

If you need complete isolation (e.g., two agents running parallel Codex tasks
against the same repo), you can:

1. Use separate project directories (copy the repo)
2. Set the `CTX_SESSION_ID` environment variable to namespace chunks per session:
   ```bash
   export CTX_SESSION_ID=agent-1
   cargo test 2>&1 | python scripts/ctx_compress.py --index --source "test:cargo" --project .
   ```

The session ID is prepended to source identifiers internally. **Note**: When using
`CTX_SESSION_ID`, include the session prefix in source prefix filters:
`--source "agent-1:file:src/"` instead of `--source "file:src/"`.

---

## Advanced Operations

### Delete Specific Sources

Remove stale index entries when files are refactored or deleted:

```bash
# Delete a specific source (exact match)
python scripts/ctx_search.py --delete-source "file:src/handlers/mod.rs" --project .

# Delete all sources matching a prefix
python scripts/ctx_search.py --delete-source "file:src/handlers/" --prefix --project .
```

### Clear All Indexed Content

Start fresh without deleting the database file:

```bash
python scripts/ctx_search.py --clear-all --project .
```

### Custom Session Window for Stats

View compression stats for a custom time window:

```bash
# Stats for last 8 hours
python scripts/ctx_stats.py --session --session-hours 8 --project .
```
