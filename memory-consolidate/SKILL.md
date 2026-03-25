---
name: memory-consolidate
description: Runs a background maintenance agent that consolidates, deduplicates, decays confidence, and compresses old sessions in the memory store. Run this skill periodically (weekly or monthly) to keep the memory store lean and high-signal. Also useful after large batches of memory-write operations. Prevents the store from growing stale or bloated over time.
version: 2.0.0
allowed-tools: "Read, Write, Bash, Glob, Grep, Edit"
disable-model-invocation: false
---

# Memory Consolidate — Maintenance Agent

You are the memory-consolidate sub-agent. Your role is to keep the memory store
accurate, lean, and high-signal. Run a full maintenance pass now.

## Step 1 — Get Current Stats

```bash
python {baseDir}/../memory/scripts/search_memory.py --stats
```

Report the current state before making changes.

## Step 2 — Run Full Consolidation

```bash
python {baseDir}/../memory/scripts/consolidate.py
```

This script handles:
- **Confidence decay**: `high → medium` after 90 days, `medium → low` after 60 more days,
  `low → archived` after 30 more days (for non-episodic memories)
- **Duplicate detection**: Flags entries with identical titles across the store
- **Session compression**: Groups episodic sessions older than 90 days into monthly summaries
  and moves originals to the `archive/` subdirectory
- **Index rebuild**: Regenerates the search index after all changes

## Step 3 — Review Duplicate Report

If duplicates were flagged, read each pair and manually merge:

```bash
cat {baseDir}/../memory/store/{path-to-first-duplicate}
cat {baseDir}/../memory/store/{path-to-second-duplicate}
```

Merge the content into the better-named file, then delete the redundant entry:

```bash
python {baseDir}/../memory/scripts/write_memory.py \
  --type {type} --category {category} --title "{merged-title}" \
  --content-file /tmp/merged-memory.md --tags "{merged-tags}" --project "{project}" \
  --overwrite
```

## Step 4 — Review Archived Entries

Check for low-confidence or archived entries that should be confirmed or removed:

```bash
python {baseDir}/../memory/scripts/search_memory.py \
  --query "" --type semantic --limit 50 | grep -i "archived\|confidence: low"
```

For each archived entry, decide:
- Still relevant → restore confidence to `medium`
- Definitely stale → leave as `archived` (never delete episodic; delete semantic/procedural if truly obsolete)

## Step 5 — Rebuild Final Index

```bash
python {baseDir}/../memory/scripts/search_memory.py --rebuild-index
```

## Step 6 — Report

```
✅ Memory Consolidation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 Entries decayed:         {N}
📦 Entries archived:        {N}
🗂️  Sessions compressed:     {N} into monthly summaries
⚠️  Duplicates flagged:      {N} (review manually)
🗃️  Index rebuilt:           {N} entries indexed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Next recommended run: ~7 days
```

## Dry Run Option

To preview changes without writing anything:

```bash
python {baseDir}/../memory/scripts/consolidate.py --dry-run
```

## Recommended Schedule

| Cadence | Trigger |
|---------|---------|
| Weekly | After 5+ sessions of active work |
| Monthly | Minimum regardless of activity |
| On-demand | After bulk memory-write operations |
| On-demand | When recall results feel noisy or outdated |
