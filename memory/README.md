# memory

The core storage skill of the OpenSite long-term memory system. This skill defines
the hierarchical directory tree structure and provides the Python scripts that all
other memory skills use to read and write entries.

## What This Skill Is

This is the **schema and rulebook** — not an action skill. It defines the store layout,
entry format, tag taxonomy, and exposes low-level read/write/search operations.

The actual memory data lives in `store/` inside this directory (gitignored).

## Store Location

```
memory/
├── SKILL.md          ← Skill instructions (versioned in git)
├── scripts/          ← Python utilities (versioned in git)
└── store/            ← Memory data (gitignored, lives only on your machine)
    ├── episodic/
    ├── semantic/
    ├── procedural/
    └── working/
```

## Scripts

| Script | Purpose |
|--------|---------|
| `write_memory.py` | Atomic write with frontmatter, dedup guard, and index update |
| `search_memory.py` | Keyword + TF-IDF search across all memory layers |
| `list_memories.py` | List all entries with optional filtering |
| `consolidate.py` | Confidence decay, duplicate detection, session compression |

No external dependencies. Python 3.8+ only.

`write_memory.py` accepts inline content via `--content`, but for multiline markdown,
code fences, or shell-sensitive text you should prefer `--content-stdin` or
`--content-file`.
