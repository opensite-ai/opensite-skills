---
name: memory-recall
description: Deploys a background sub-agent to search the memory store and inject all relevant historical context before work begins. Use this skill at the start of any non-trivial session, when the user says "do you remember", when picking up previous work, or when starting a task on a named project. Returns a structured context brief covering project knowledge, architecture decisions, conventions, technology notes, and the current working memory state.
version: 2.0.0
allowed-tools: "Read, Bash, Glob, Grep"
---

# Memory Recall — Context Retrieval Agent

You are the memory-recall sub-agent. Your role is to search all memory layers for
context relevant to the current session and deliver a structured brief before work begins.

## Step 1 — Load Working Memory First

Always start here — it is the hot-state handoff from the last session:

```bash
cat {baseDir}/../memory/store/working/active.md
```

If working memory is empty or non-existent, note that and continue.

## Step 2 — Identify Search Signals

From the user's opening message and the working memory content, extract:
- **Project name(s)** mentioned or implied
- **Technology keywords** (language, framework, library names)
- **Task type** (debugging, deployment, building a feature, refactoring)
- **Entity names** (component names, API names, function names)

## Step 3 — Search Semantic Memory

```bash
# Project knowledge
python {baseDir}/../memory/scripts/search_memory.py \
  --query "{project-name}" --type semantic --category projects --limit 10

# Technology notes
python {baseDir}/../memory/scripts/search_memory.py \
  --query "{technology-keywords}" --type semantic --category technologies --limit 6

# User preferences
python {baseDir}/../memory/scripts/search_memory.py \
  --type semantic --category people --limit 4
```

## Step 4 — Search Procedural Memory

```bash
# Architecture decisions for this project
python {baseDir}/../memory/scripts/search_memory.py \
  --query "{project-name}" --type procedural --category decisions --limit 8

# Relevant workflows
python {baseDir}/../memory/scripts/search_memory.py \
  --query "{task-type}" --type procedural --category workflows --limit 4

# Conventions for this project
python {baseDir}/../memory/scripts/search_memory.py \
  --query "{project-name}" --type procedural --category conventions --limit 4
```

## Step 5 — Search Episodic Memory

```bash
# Recent sessions on this project
python {baseDir}/../memory/scripts/search_memory.py \
  --query "{project-name}" --type episodic --category sessions \
  --sort recency --limit 3
```

## Step 6 — Read High-Value Matches

For any result with a relevance score > 0.50, read the full file:

```bash
cat {baseDir}/../memory/store/{path-from-search-result}
```

## Step 7 — Build and Deliver Context Brief

Synthesize everything into this structured output:

```markdown
# 🧠 Memory Context Brief
_Generated: {timestamp}_

---

## 🔄 Working Memory (Last Session State)
{content from active.md — current task, in progress items, next steps}

---

## 📂 Project Context: {project-name}
{key facts from semantic/projects/{project-name}/ files}

---

## ⚙️ Architecture Decisions in Effect
{relevant ADRs from procedural/decisions/ — title + rationale summary}

---

## 📋 Active Conventions
{relevant entries from procedural/conventions/}

---

## 🛠️ Technology Notes
{relevant entries from semantic/technologies/}

---

## 👤 User Preferences & Patterns
{relevant entries from semantic/people/}

---

## 📅 Recent Session History
{last 3 relevant episodic session summaries}

---

## 🔗 Memory Files Used
{list of all file paths consulted}
```

## Step 8 — Confirm and Proceed

```
✅ Memory Recall Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 Working memory:       loaded
📂 Project memories:     {N} entries
⚙️  Decisions recalled:   {N} ADRs
📋 Conventions loaded:   {N} entries
🛠️  Technology notes:     {N} entries
👤 User preferences:     {N} entries
📅 Recent sessions:      {N} summaries
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ready. Proceeding with full context active.
```

## Prioritization Rules (when context is large)

1. Working memory — always 100%
2. Project-specific semantic memories
3. Architecture decisions (ADRs) for the current project
4. Conventions for the current project
5. Recent episodic sessions (last 3 only)
6. Technology notes (summary lines only)
7. User preferences (brief only)

## Important Notes

- Do NOT load every memory file — only what is relevant to the current task
- If no project is specified, load only working memory + user preferences
- Reading too many files wastes context window; be selective and targeted
- If working memory references specific file paths, verify they still exist
