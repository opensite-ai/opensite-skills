# Activation Guide

## Best-Fit Tasks
- Context virtualization for extending effective context window across AI coding agents.
- Best trigger phrases: long session management, large output compression, context window optimization, compaction survival, output indexing, search indexed content, checkpoint session state.

## Explicit Invocation
- `Use $context-management when working in long sessions, when tool outputs are large (logs, diffs, snapshots), or when resuming after compaction. Provides SQLite FTS5 indexing, BM25 search, deterministic compression, and session checkpointing.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked scripts you need.
- All scripts are Python 3.8+ with zero external dependencies.
- Data is stored in `.ctx/` relative to the project root (auto-added to `.gitignore` on first run).
- This skill complements the `memory` skills (long-term persistence) with session-level context optimization.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
- Scripts can be invoked with relative paths (`scripts/ctx_index.py`) from the skill's installation directory.

## Quick Reference

```bash
# Index content
cat output.txt | python scripts/ctx_index.py --source "type:name" --project .

# Search indexed content
python scripts/ctx_search.py --query "keywords" --project .

# Compress large output (and optionally index)
command 2>&1 | python scripts/ctx_compress.py --lines 40 --index --source "type:name" --project .

# Save session checkpoint (auto-captures git context)
python scripts/ctx_checkpoint.py save --project . --task "description" --completed "items" --next-steps "items"

# Load checkpoint after compaction
python scripts/ctx_checkpoint.py load --project .

# Load checkpoint as JSON
python scripts/ctx_checkpoint.py load --project . --json

# Delete specific source
python scripts/ctx_search.py --delete-source "file:name" --project .

# Clear all indexed content
python scripts/ctx_search.py --clear-all --project .
```
