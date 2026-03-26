# Context Management Skill

> Extend effective context window across all AI coding agents with zero external dependencies.

## What It Does

Large tool outputs (file reads, git diffs, test runs, Playwright snapshots, log dumps)
burn through the context window rapidly. Agents with hook support (Claude Code) can
intercept these automatically. Agents without hooks (Codex CLI) cannot.

This skill provides the same "context virtualization" as a portable, agent-driven
workflow: the agent invokes these tools explicitly instead of hooks doing it implicitly.

### Core Features

- **SQLite FTS5 Indexing** — Store full outputs in a searchable database
- **BM25 Ranked Search** — Retrieve targeted snippets with relevance scores
- **Deterministic Compression** — Reduce large outputs to fixed line budgets
- **Session Checkpointing** — Survive context compaction with state persistence
- **Zero Dependencies** — Pure Python 3.8+, works everywhere

## Quick Start

```bash
# Index a large test output
cargo test 2>&1 | python scripts/ctx_compress.py \
  --lines 40 --index --source "test:cargo" --project .

# Later, search for specific failures
python scripts/ctx_search.py --query "FAILED assertion" --project .

# Save state before compaction
python scripts/ctx_checkpoint.py save --project . \
  --task "Implementing feature X" \
  --completed "item1, item2" \
  --next-steps "tests, docs"

# Reload after compaction
python scripts/ctx_checkpoint.py load --project .
```

## Installation

This skill is part of the [opensite-skills](https://github.com/opensite-ai/opensite-skills)
repository. Install via symlink:

```bash
cd /path/to/opensite-skills
./setup.sh  # Creates symlinks for Claude Code, Codex, Cursor
```

Or copy the `context-management/` directory to your agent's skills directory.

## Verification

Run the smoke-test script after installation:

```bash
cd /path/to/context-management
./scripts/test_ctx.sh
```

This validates that all scripts work correctly on your platform.

## Documentation

- **Full documentation**: [SKILL.md](SKILL.md)
- **Activation guide**: [references/activation.md](references/activation.md)

## Platform Notes

### FTS5 Availability

Most platforms ship Python with SQLite FTS5 support (macOS, Windows, standard Linux).

On platforms without FTS5 (some Alpine-based Docker images, older Linux distros):
- The skill falls back to FTS4 automatically
- Search works, but results are unranked (BM25 unavailable)
- All other features work normally

### Concurrent Agents

Multiple agents working in the same project directory share the same `.ctx/context.db`.
SQLite WAL mode handles concurrent access safely for typical use cases.

For complete isolation, use separate project directories or the `CTX_SESSION_ID`
environment variable (see SKILL.md for details).

## Related Projects

This skill implements the same context virtualization pattern as
[mksglu/context-mode](https://github.com/mksglu/context-mode), but as a portable,
zero-dependency Python toolkit that works across all AI coding agents.

## License

MIT
