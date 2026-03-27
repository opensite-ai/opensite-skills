---
name: memory
description: "The OpenSite persistent long-term memory store. Provides a hierarchical filesystem tree for all agent memories across four cognitive layers: episodic (session history), semantic (project/tech/user knowledge), procedural (decisions, workflows, conventions), and working (active session state). Use this skill to directly read, write, search, or inspect memory entries. For automated session capture use memory-write; for context retrieval before a task use memory-recall; for periodic maintenance use memory-consolidate."
allowed-tools: "Read, Write, Bash, Glob, Grep, Edit"
metadata:
  version: 2.0.0
---

# Memory Store

You have access to the OpenSite persistent memory store — a hierarchical directory tree of
markdown files that persists knowledge across all sessions and AI engines.

## Store Location

The store lives at `{baseDir}/store/` relative to this skill. The canonical path is set by
the installing engine's symlink. All scripts use `Path(__file__).resolve()` so they always
find the store regardless of which engine invokes them.

## Memory Tree Structure

```
store/
├── episodic/
│   ├── sessions/         ← YYYY-MM-DD-{slug}.md per session
│   │   └── archive/      ← Monthly summaries of old sessions
│   └── events/           ← Significant milestones and breakthroughs
├── semantic/
│   ├── projects/         ← {project-name}/ subfolder per project
│   ├── people/           ← User preferences, collaborators, clients
│   ├── technologies/     ← Libraries, frameworks, versions, gotchas
│   └── domain/           ← Business / domain facts
├── procedural/
│   ├── workflows/        ← Step-by-step repeatable procedures
│   ├── decisions/        ← Architecture Decision Records (ADRs)
│   └── conventions/      ← Code style, naming rules, team patterns
└── working/
    └── active.md         ← Hot context for the current session only
```

## Memory Entry Format

Every memory file uses this structure:

```markdown
---
id: {8-char-uuid}
type: episodic|semantic|procedural|working
category: sessions|events|projects|people|technologies|domain|workflows|decisions|conventions|active
title: Human readable title
tags: [tag1, tag2, tag3]
project: project-name or null
created: YYYY-MM-DD
updated: YYYY-MM-DD
confidence: high|medium|low|archived
---

# Title

## Summary
1-3 sentence summary used for fast retrieval without reading the body.

## Content
Full memory content here.
```

## Common Operations

### Search for relevant memories
```bash
python {baseDir}/scripts/search_memory.py --query "rust axum" --type semantic
python {baseDir}/scripts/search_memory.py --query "deploy" --type procedural --limit 5
python {baseDir}/scripts/search_memory.py --type episodic --sort recency --limit 3
```

### Write a new memory entry
```bash
python {baseDir}/scripts/write_memory.py \
  --type semantic \
  --category technologies \
  --title "Axum Tower Middleware Pattern" \
  --content "When adding middleware in Axum 0.8+, use tower::ServiceBuilder..." \
  --tags "rust,axum,middleware,tower" \
  --project opensite-api
```

### Write multiline markdown safely
Use stdin or a file when the content includes markdown, code fences, backticks, or multiple paragraphs.

```bash
cat <<'EOF' | python {baseDir}/scripts/write_memory.py \
  --type procedural \
  --category decisions \
  --title "ADR: Use Axum over Actix-Web" \
  --content-stdin \
  --tags "rust,axum,architecture,adr" \
  --project opensite-api
## Context
Needed async HTTP framework...

## Decision
Axum...

## Rationale
...
EOF
```

### Write a procedural decision (ADR)
```bash
python {baseDir}/scripts/write_memory.py \
  --type procedural \
  --category decisions \
  --title "ADR: Use Axum over Actix-Web" \
  --content-file /tmp/axum-adr.md \
  --tags "rust,axum,architecture,adr" \
  --project opensite-api
```

### Read current working memory (active session state)
```bash
cat {baseDir}/store/working/active.md
```

### List all memories with summaries
```bash
python {baseDir}/scripts/list_memories.py --brief
python {baseDir}/scripts/list_memories.py --type procedural
```

### View full memory stats
```bash
python {baseDir}/scripts/search_memory.py --stats
```

## Memory Hygiene Rules

1. **One concept per file** — never bundle unrelated facts
2. **Summaries are mandatory** — they enable fast search without full reads
3. **Tags are required** — minimum 2, maximum 8 per entry
4. **Project field is required** when the memory is project-specific
5. **Confidence scoring** — mark `low` for inferred or uncertain facts
6. **Deduplication first** — search before writing to avoid duplicates
7. **Never hard-delete episodic memories** — set confidence to `archived` instead

## Standard Tag Taxonomy

```
Technology:  rust, axum, rails, react, typescript, nextjs, tailwind, shadcn,
             postgres, redis, fly-io, cloudflare, vercel, node, ruby, crystal
Task type:   debugging, architecture, deployment, refactoring, api-design,
             performance, security, testing, ci-cd
Quality:     verified, inferred, deprecated, experimental, critical, temporary
Relation:    decision, blocker, prerequisite, alternative, supersedes, adr
```
