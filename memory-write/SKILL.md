---
name: memory-write
description: Deploys a background sub-agent to extract and persist important information from the current conversation into the long-term memory store. Invoke this skill at the end of a work session, after major architectural decisions, after fixing a non-trivial bug, or whenever the user says "save this", "remember this", or "store to memory". The agent analyzes the conversation for decisions, preferences, patterns, and facts then writes them to the correct memory layer automatically.
version: 2.0.0
allowed-tools: "Read, Write, Bash, Glob, Grep, Edit"
---

# Memory Write — Session Capture Agent

You are the memory-write sub-agent. Your role is to analyze the current session and
persist all valuable knowledge to the long-term memory store before the context is lost.

## Trigger Conditions

Run this skill when:
- The user says "save that", "remember this", "store to memory", "write to memory"
- A session is ending (user says goodbye, wraps up, asks for summary)
- A significant architectural or technology decision was just made
- A non-trivial bug was found and fixed (document root cause + fix)
- New project structure, file paths, or API contracts were established
- A user preference or working pattern was explicitly stated

## Step 1 — Read Current Working Memory

```bash
cat {baseDir}/../memory/store/working/active.md
```

Understand the existing session state before overwriting it.

## Step 2 — Extract Memory Candidates

Analyze the conversation transcript for items in all four layers:

**Episodic (sessions, events):**
- What was the main task or goal?
- What was the final outcome or current state?
- What errors or blockers were encountered and how resolved?

**Semantic (projects, technologies, people, domain):**
- What project-specific facts emerged? (file paths, data models, API structures)
- What technology facts were confirmed? (version numbers, library behavior, gotchas)
- What user preferences were expressed? (tech choices, style, priorities)

**Procedural (decisions, workflows, conventions):**
- Was an architectural decision made with clear rationale?
- Was a repeatable workflow or process established?
- Was a code convention or naming standard identified?

## Step 3 — Check for Duplicates Before Writing

For each candidate item, search first:

```bash
python {baseDir}/../memory/scripts/search_memory.py --query "{topic keywords}" --limit 5
```

- Score > 0.80: Update the existing entry instead of creating a new one
- Score 0.40–0.80: Create new entry with a `related:` note in the content
- Score < 0.40: Create fresh entry

## Step 4 — Write Session Summary (Always)

```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type episodic \
  --category sessions \
  --title "Session: {YYYY-MM-DD} — {brief-3-word-slug}" \
  --content "## Goal\n{what we set out to do}\n\n## Outcome\n{what was accomplished}\n\n## Key Decisions\n{decisions made}\n\n## Problems Solved\n{issues encountered and resolutions}\n\n## Next Steps\n{what remains}" \
  --tags "{comma,separated,tags}" \
  --project "{active-project-or-null}"
```

## Step 5 — Write Semantic Memories

Write one file per distinct fact:

```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type semantic \
  --category technologies \
  --title "{fact title}" \
  --content "{detailed fact}" \
  --tags "{tags}" \
  --project "{project}"
```

For project-specific knowledge:
```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type semantic \
  --category projects \
  --title "{project}: {fact}" \
  --content "{fact details}" \
  --tags "{tags}" \
  --project "{project-name}"
```

## Step 6 — Write Procedural Memories

For Architecture Decision Records:
```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type procedural \
  --category decisions \
  --title "ADR: {Decision Title}" \
  --content "## Context\n{why this decision was needed}\n\n## Decision\n{what was decided}\n\n## Rationale\n{why this option was chosen}\n\n## Trade-offs\n{what we gave up}\n\n## Status\nAccepted" \
  --tags "adr,{relevant-tech-tags}" \
  --project "{project}"
```

For established workflows:
```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type procedural \
  --category workflows \
  --title "{Workflow Name}" \
  --content "## Steps\n1. {step}\n2. {step}\n\n## Notes\n{gotchas}" \
  --tags "workflow,{tech-tags}" \
  --project "{project}"
```

## Step 7 — Update Working Memory

Replace active.md with the next-session handoff state:

```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type working \
  --category active \
  --title "Active Context" \
  --content "## Current Project\n{project name}\n\n## Active Task\n{task description and current status}\n\n## In Progress\n{what is partially done}\n\n## Next Steps\n{ordered list of what comes next}\n\n## Active Files\n{key files being worked on}\n\n## Open Questions\n{unresolved decisions or unknowns}\n\n## Last Session\n{YYYY-MM-DD} — {brief summary}" \
  --tags "working,active,session" \
  --overwrite
```

## Step 8 — Report

Confirm completion with a structured summary:

```
✅ Memory Write Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📅 Episodic:    {N} session entries written
🧠 Semantic:    {N} entries ({N} new, {N} updated)
⚙️  Procedural:  {N} entries ({N} decisions, {N} workflows)
🔄 Working:     Updated for next session
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Session slug: {slug}
```

## Quality Rules

- **Be selective** — only write what would be useful in a future session
- **Be specific** — "fixed Axum router middleware ordering bug" not "fixed bug"
- **One fact per file** — never bundle unrelated concepts
- **ADRs need rationale** — always capture *why*, not just *what*
- **Confidence: low** for inferences; **high** only for confirmed facts
- **Never skip** the working memory update — it bridges sessions
