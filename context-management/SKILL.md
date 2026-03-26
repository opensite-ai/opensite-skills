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
version: 1.0.0
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

All scripts live in `{baseDir}/scripts/` relative to this SKILL.md. They use
`Path(__file__).resolve()` for portable path resolution. All are Python 3.8+
with zero external dependencies.

### 1. ctx_index.py — Index Content into FTS5

Index large outputs so they stay out of context but remain searchable.

```bash
# Index from stdin (pipe a command's output)
cat large_file.rs | python {baseDir}/scripts/ctx_index.py \
  --source "file:src/handlers/mod.rs" \
  --project /path/to/project

# Index from a file
python {baseDir}/scripts/ctx_index.py \
  --source "git:diff-main" \
  --file /tmp/git_diff_output.txt \
  --project /path/to/project

# Index inline content
python {baseDir}/scripts/ctx_index.py \
  --source "test:cargo-test" \
  --content "$(cargo test 2>&1)" \
  --project /path/to/project

# Index with tags for filtering
python {baseDir}/scripts/ctx_index.py \
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
python {baseDir}/scripts/ctx_search.py \
  --query "error handling AppError" \
  --project /path/to/project

# Search with source filter
python {baseDir}/scripts/ctx_search.py \
  --query "middleware tower" \
  --source "file:src/" \
  --project /path/to/project

# Search with tag filter and limit
python {baseDir}/scripts/ctx_search.py \
  --query "deploy timeout" \
  --tags "production" \
  --limit 5 \
  --project /path/to/project

# List all indexed sources
python {baseDir}/scripts/ctx_search.py \
  --list-sources \
  --project /path/to/project

# Show DB stats
python {baseDir}/scripts/ctx_search.py \
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
cat huge_log.txt | python {baseDir}/scripts/ctx_compress.py

# Compress to specific line budget
git diff HEAD~5 | python {baseDir}/scripts/ctx_compress.py --lines 30

# Compress and index simultaneously (recommended workflow)
cargo test 2>&1 | python {baseDir}/scripts/ctx_compress.py \
  --lines 40 \
  --index \
  --source "test:cargo-test" \
  --project /path/to/project

# Compress a file
python {baseDir}/scripts/ctx_compress.py \
  --file /tmp/large_output.txt \
  --lines 60
```

**What it does:**
- Reads full input, extracts a deterministic summary within the line budget
- Prioritizes: errors/warnings first, then structure (headings/signatures), then content
- Appends a `[compressed: N/M lines, full content indexed as {source}]` footer
- With `--index`, also stores the full uncompressed content in FTS5

### 4. ctx_checkpoint.py — Session State Persistence

Save and restore session state across Codex compaction boundaries.

```bash
# Save a checkpoint
python {baseDir}/scripts/ctx_checkpoint.py save \
  --project /path/to/project \
  --task "Implementing OAuth2 flow for customer-sites" \
  --completed "Added OAuth routes, Created token model" \
  --in-progress "Writing token refresh middleware" \
  --next-steps "Add tests, Update AGENTS.md" \
  --decisions "Using tower middleware for auth, JWT with RS256" \
  --context "Branch: feature/oauth2, Tests passing except refresh"

# Load the latest checkpoint
python {baseDir}/scripts/ctx_checkpoint.py load \
  --project /path/to/project

# List all checkpoints
python {baseDir}/scripts/ctx_checkpoint.py list \
  --project /path/to/project
```

**What it does:**
- Writes a structured markdown checkpoint to `.ctx/checkpoint.md`
- Archives previous checkpoints with timestamps
- On load, returns the checkpoint content for context injection
- Designed to be called before compaction and after resuming

---

## Recommended Workflows

### Workflow A: Large Output Routing (Primary Use Case)

When a command will produce large output, route it through compress+index:

```bash
# Instead of raw: cargo test 2>&1
# Do this:
cargo test 2>&1 | python {baseDir}/scripts/ctx_compress.py \
  --lines 40 --index --source "test:cargo-test" --project .

# Later, find specific test failures:
python {baseDir}/scripts/ctx_search.py \
  --query "FAILED assertion" --project .
```

### Workflow B: File Reading with Indexing

When reading large files, index them and work from search:

```bash
# Index a large file
python {baseDir}/scripts/ctx_index.py \
  --source "file:src/handlers/mod.rs" \
  --file src/handlers/mod.rs --project .

# Search for specific content
python {baseDir}/scripts/ctx_search.py \
  --query "fn handle_request" --project .
```

### Workflow C: Compaction Survival

Before context compaction, checkpoint your state:

```bash
# Save state
python {baseDir}/scripts/ctx_checkpoint.py save \
  --project . \
  --task "Current task description" \
  --completed "Done items" \
  --in-progress "Current work" \
  --next-steps "What to do next"

# After compaction, reload
python {baseDir}/scripts/ctx_checkpoint.py load --project .
```

### Workflow D: Session Start (combine with memory-recall)

At session start, load both memory context and any existing checkpoints:

```bash
# Load checkpoint if exists
python {baseDir}/scripts/ctx_checkpoint.py load --project .

# Check what's been indexed
python {baseDir}/scripts/ctx_search.py --stats --project .
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

Add this to your project's `.gitignore`:

```
# Context management data (session-local, not committed)
.ctx/
```
