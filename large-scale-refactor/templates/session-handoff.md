# REFACTOR SESSION HANDOFF
# ========================
# This file is written by the agent at the END of every session and read at the
# START of the next. Commit it with every batch of changes so it stays in sync
# with the git history.
#
# A fresh agent context — same or different model, same or different platform —
# reads this file as its first action before touching any code.
# The approved spec is always the authoritative source of truth; this file is
# the resumption bridge that prevents re-reading the entire git log.
#
# Fill in every field. Delete placeholder text before committing.
# Lines beginning with '#' are comments and may be removed.

---
Task: <task-name>                   # e.g. "js-to-ts-migration"
Last session: <ISO-8601 datetime>   # e.g. "2026-03-27T14:32:00Z"
Agent: <model / platform>           # e.g. "Claude Sonnet 4.5 / Claude Code"
Session number: <N>                 # increment each session, starting at 1
Spec: <path or URL>                 # e.g. "TASK_SPEC.md" or link to PR description
---

## Progress

### Completed subtasks
<!-- List every subtask that is fully done, committed, and verified.
     Include the commit SHA or PR link so the next agent can confirm. -->

- [ ] Subtask 1 — <description> — commit <sha>
- [ ] Subtask 2 — <description> — commit <sha>

### In-progress subtask
<!-- At most ONE subtask should be in progress at the end of a session.
     If a subtask was partially completed, describe exactly where it stopped. -->

**Subtask N** — <description>
- Percentage complete: <N>%
- Files processed so far: <N> of <total>
- Last file touched: `<path/to/last-file-processed>`
- Next file to process: `<path/to/next-file-to-touch>`

### Remaining subtasks
<!-- Everything not yet started, in planned execution order. -->

- [ ] Subtask <N+1> — <description> — affects ~<N> files in `<directory>`
- [ ] Subtask <N+2> — <description> — affects ~<N> files in `<directory>`

---

## Files Remaining

<!-- Exhaustive list of files not yet processed in the in-progress subtask.
     The next agent should process ONLY these files, in this order.
     Do NOT re-process files already committed (they appear in Completed subtasks). -->

```
<path/to/file-001>
<path/to/file-002>
<path/to/file-003>
```

Total remaining in current subtask: <N>

---

## State to Carry Forward

### Decisions made this session
<!-- Document every non-obvious decision the next agent must respect.
     Include the reasoning so the decision can be revisited if needed. -->

- **Decision**: <what was decided>
  **Reason**: <why — what alternatives were considered and rejected>
  **Impact**: <which future files or subtasks this affects>

### Edge cases discovered
<!-- Files or patterns that required special handling beyond the spec's standard approach. -->

- `<path/to/file>` — <why this file needed special treatment and what was done>

### Files requiring special handling
<!-- Files in the remaining list that need a non-standard approach.
     The next agent must read these notes before touching the listed files. -->

- `<path/to/file>` — <instructions for non-standard handling>

### Patterns confirmed
<!-- Transformations that were validated to work correctly and should be applied
     consistently to all remaining files without further review. -->

- <Pattern description> — confirmed working in <N> files, safe to apply broadly

---

## Drift Check Log (this session)

<!-- Paste the most recent DRIFT CHECK output here.
     If multiple drift checks were run, include only the final one.
     This lets the next agent verify no violations were left unresolved. -->

```
DRIFT CHECK
===========
Files touched this session: <N>
Task: <task-name>

1. Does every changed file appear in the IN SCOPE list?      YES / NO
   Evidence: <one sentence>

2. Did I add any new files not defined in the spec?          YES / NO
   List: <filenames, or N/A>

3. Did I add, remove, or modify any dependency?             YES / NO
   List: <manifests changed, or N/A>

4. Did I make any change that fails the Substitution Test?  YES / NO

5. Did I create any new abstraction, utility, or system?    YES / NO

All answers NO — continuing. / ⏸ HALTED — see Active Blockers below.
```

---

## Active Blockers

<!-- CRITICAL: List every unresolved checkpoint, question, or blocker that
     requires human input before the next session can begin.
     If there are no blockers, write "None." -->

None.

<!-- If blockers exist, use this format:
- **BLOCKER**: <what is blocking progress>
  **Type**: spec_ambiguity | out_of_scope_file | new_dependency | new_abstraction | test_failure | other
  **Context**: <file(s), line(s), or situation>
  **Options**:
    A. <option and implications>
    B. <option and implications>
    C. Abort task and preserve current state for human review
  **Recommendation**: <agent's recommendation>
  **Status**: Awaiting human instruction
-->

---

## Observations Log (this session)

<!-- Reference to any new entries added to OBSERVATIONS.md this session.
     Do not duplicate content — just summarise what was added. -->

- Added <N> new observation(s) to OBSERVATIONS.md:
  - `<path>` — <brief description> (Severity: <level>)

---

## Resumption Instructions for Next Agent

<!-- Pre-filled checklist. The next agent reads this before touching any file. -->

1. Read the approved spec at `<spec path>` — this is the authoritative source of truth.
2. Read this file in full — do not rely on conversation history.
3. Confirm: all subtasks listed under **Completed** have their commits present in `git log`.
4. Load the `.refactor-scope-allowlist` and run `python scripts/verify_scope.py` to confirm
   the current working tree is clean.
5. Resume the **In-progress subtask** at the file listed under "Next file to process".
6. Apply the **Decisions made this session** and **Files requiring special handling** notes
   before touching any file in their scope.
7. Resolve any **Active Blockers** before writing code — surface them to the human if needed.
8. Run a DRIFT CHECK after every <cadence> files (see spec § 3.2 for the correct cadence).
9. Update this file and commit it at the end of your session.