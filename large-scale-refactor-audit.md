# `large-scale-refactor` Skill — Pre-Release Audit Report

**Repo:** [opensite-ai/opensite-skills](https://github.com/opensite-ai/opensite-skills)  
**Path:** [`large-scale-refactor/`](https://github.com/opensite-ai/opensite-skills/tree/main/large-scale-refactor)  
**Audit date:** 2026-03-27  
**Auditor:** Perplexity Model Council + Deep Research pass  
**Status:** 🟡 Ready with required fixes (see Critical/High items below)

---

## Executive Summary

The `large-scale-refactor` skill is structurally sound and conceptually complete. The core SKILL.md (§§ 1–8), the session handoff protocol, the drift detection checkpoint, and the Change Manifest format are all production-quality and ready to promote. However, **one blocker** must be resolved before open source promotion: the test suite hardcodes an absolute local machine path (`/Users/jordanhudgens/code/dashtrack/...`) that both exposes an internal project name and breaks every clone of the repo. Three medium-priority issues also need resolution before the skill can be recommended publicly. The remaining findings are enhancements or cosmetic.

---

## Issue Registry

### 🔴 CRITICAL — Must fix before open source promotion

#### CRIT-1: Hardcoded absolute paths in test suite

**File:** `scripts/test_verify_scope.py`  
**Lines affected:** Two `sys.path.insert` calls and two `subprocess.run` calls

The test file contains hardcoded absolute paths referencing a local machine:

```python
# BROKEN — these paths exist only on Jordan's machine
sys.path.insert(0, '/Users/jordanhudgens/code/dashtrack/opensite-skills/large-scale-refactor/scripts')
subprocess.run(['python', '/Users/jordanhudgens/code/dashtrack/.../verify_scope.py'])
```

**Impact:** Every test will fail with `ModuleNotFoundError` / `FileNotFoundError` on any other machine. As an open source project, this means every contributor and user who runs the test suite gets a broken experience on first try. It also inadvertently discloses the internal project name `dashtrack`.

**Fix — replace with dynamic path resolution:**

```python
import os
import sys

# At the top of the test file, resolve scripts dir dynamically
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
VERIFY_SCOPE = os.path.join(SCRIPTS_DIR, 'verify_scope.py')

# Replace sys.path.insert with:
sys.path.insert(0, SCRIPTS_DIR)

# Replace subprocess calls with:
subprocess.run(['python', VERIFY_SCOPE], ...)
```

---

### 🟠 HIGH — Should fix before open source promotion

#### HIGH-1: `verify_scope.py` glob pattern matching is broken for `*.ext` patterns

**File:** `scripts/verify_scope.py`  
**Function:** `check_scope_compliance()`

Current logic:

```python
if pattern in file or file.startswith(pattern.rstrip('/') + '/') or file == pattern:
```

The string-`in` check does not handle glob patterns. For example, if the allowlist contains `*.js`, the expression `'*.js' in 'src/Button.js'` evaluates to `False` — meaning every `.js` file is flagged as a scope violation despite being in the allowlist. This is a silent correctness failure that would send false-positive alerts on the most common migration type (JS→TS).

**Fix — use `fnmatch` for glob patterns:**

```python
import fnmatch
from pathlib import Path

def check_scope_compliance(changed_files, allowlist):
    out_of_scope = []
    for file in changed_files:
        matched = False
        for pattern in allowlist:
            # Directory prefix match
            if pattern.endswith('/') and file.startswith(pattern):
                matched = True
                break
            # Glob pattern match (*.js, **/*.tsx, etc.)
            if fnmatch.fnmatch(file, pattern) or fnmatch.fnmatch(os.path.basename(file), pattern):
                matched = True
                break
            # Exact match
            if file == pattern:
                matched = True
                break
        if not matched:
            out_of_scope.append(file)
    return out_of_scope
```

---

#### HIGH-2: `generate_allowlist.py` regex is too narrow — will silently produce empty allowlists

**File:** `scripts/generate_allowlist.py`  
**Line:** `dir_patterns = re.findall(r'src/\w+/|tests/|components/|hooks/', line)`

This regex is hardcoded to match only `src/`, `tests/`, `components/`, and `hooks/`. Any project using `app/`, `lib/`, `pages/`, `services/`, `pkg/`, or any other directory name will produce an empty allowlist, and the script will exit with `⚠️ No patterns found in spec`.

**Fix — extract any path-like token from IN SCOPE lines:**

```python
def extract_scope_patterns(spec_content):
    patterns = []
    in_scope_section = False

    for line in spec_content.split('\n'):
        if re.search(r'\*\*IN SCOPE\*\*|^## IN SCOPE', line):
            in_scope_section = True
            continue
        if in_scope_section:
            if re.search(r'\*\*OUT OF SCOPE\*\*|^## OUT OF SCOPE|^## ', line):
                break
            # Extract any checked item (- [x] ...) from IN SCOPE
            match = re.match(r'\s*-\s*\[x\]\s*(.*)', line, re.IGNORECASE)
            if match:
                raw = match.group(1).strip()
                # Extract glob patterns (*.ext) 
                globs = re.findall(r'\*\.\w+', raw)
                patterns.extend(globs)
                # Extract directory/path-like tokens (anything with / or ending in /)
                paths = re.findall(r'[\w\-\.]+(?:/[\w\-\./\*]*)+', raw)
                patterns.extend(paths)
    return patterns
```

---

#### HIGH-3: `SKILL.md.bak` must be removed from the repository

**File:** `large-scale-refactor/SKILL.md.bak`  
**Size:** 16,154 bytes

A `.bak` file in a public repository is a maintenance antipattern and a source of confusion. Contributors and automated tools cannot know whether the `.bak` is the authoritative version. Additionally, the `.bak` contains the richer YAML frontmatter structure (with `platforms:` block and `activation_patterns:` as a proper YAML list) that was lost in the live `SKILL.md` during the implementation pass — the presence of both files will confuse anyone evaluating the structure.

**Fix:** Delete `SKILL.md.bak`. The relevant content from its richer frontmatter (see IMPROVE-1 below) should be merged into the live `SKILL.md` before deletion.

---

### 🟡 MEDIUM — Recommended before promotion

#### MED-1: SKILL.md frontmatter is a regression from the intended structure

**File:** `large-scale-refactor/SKILL.md`

The live `SKILL.md` uses a flat, minimal frontmatter:

```yaml
---
name: large-scale-refactor
description: "Guardrails, protocols..."
metadata:
  author: opensite-ai
  version: 1.0.0
  tags: refactor, migration, long-running, multi-agent, guardrails, agentic
---
```

The `SKILL.md.bak` preserves the richer structure from the Model Council design, which includes the `platforms:` block and `activation_patterns:` as a proper YAML sequence. Per the Agent Skills open standard, the `metadata:` wrapper is unnecessary — `author`, `version`, and `tags` should be top-level keys. The `description` should use a YAML folded block scalar (`>`) rather than a quoted string for readability.

**Recommended frontmatter (merge of both versions):**

```yaml
---
name: large-scale-refactor
description: >
  Guardrails, protocols, and operating constraints for large-scale, long-running,
  or parallelized AI coding tasks — migrations, codebase-wide refactors, framework
  upgrades, and any task touching 50+ files. Prevents scope creep, context drift,
  silent compounding errors, and emergent behavior outside the defined task boundary.
  Use when refactoring across files, migrating frameworks, upgrading dependencies,
  or replacing patterns throughout a codebase.
author: opensite-ai
version: 1.0.0
license: MIT
tags:
  - refactor
  - migration
  - long-running
  - multi-agent
  - guardrails
  - agentic
platforms:
  claude-code: { context: auto, invoke: automatic }
  codex: { invoke: automatic }
  cursor: { invoke: /large-scale-refactor }
  copilot: { invoke: /large-scale-refactor }
  qoder-quest: { scenario: "Code with Spec", environment: remote }
  factory-droid: { invoke: automatic }
activation_patterns:
  - "refactor * across"
  - "migrate * to"
  - "upgrade * from"
  - "replace all"
  - "update every"
  - "rename * throughout"
  - "convert all"
  - "remove all instances"
  - "batch * across the codebase"
  - files_touched_estimate: ">= 50"
---
```

---

#### MED-2: Missing normative content in SKILL.md — context flushing and net-new code threshold

Two key guardrails from the Model Council synthesis appear only in README.md and IMPLEMENTATION_SUMMARY.md, not in the normative SKILL.md. Agents reading only SKILL.md (the standard entry point) will miss these.

**Gemini's context flushing protocol** — add as § 6.2 to the Context Persistence section:

```markdown
### 6.2 Context Flushing Protocol (Anti-Degradation)

Agent performance degrades measurably as context windows fill with accumulated
file diffs. To counter this, the agent actively flushes context between batches.

**After completing each batch:**
1. Commit and push all changes.
2. Write the session handoff file (§ 6.1).
3. **Discard from active context**: all file diffs, modified file contents, and
   intermediate reasoning from the completed batch.
4. **Reload into fresh context**: the approved spec + the latest `.refactor-session.md`
   + the next batch file list only.

**Context flush trigger signals** — perform an immediate flush if any of these appear:
- Referencing a decision made more than 2 batches ago without consulting `.refactor-session.md`
- Uncertainty about the original task without re-reading the spec
- Making changes that "feel right" based on pattern matching rather than spec compliance
```

**Gemini's net-new code threshold** — add as § 2.5:

```markdown
### 2.5 Net-New Code Threshold

If completing any single change requires writing more than **50 lines of net-new
logic** (not counting type annotations, renamed identifiers, or structural reformatting),
the agent has likely lost the thread.

> **50-line rule**: If you are about to write more than 50 lines of net-new logic
> to accomplish a refactoring step, stop. Log the situation in OBSERVATIONS.md.
> Halt for human review before proceeding.

This threshold exists because large-scale refactors should primarily *transform*
existing patterns, not *invent* new ones. Exceeding 50 lines of net-new logic almost
always indicates scope creep or a task that requires architectural discussion.
```

---

#### MED-3: README.md contains inaccurate and broken references

**File:** `large-scale-refactor/README.md`

Three issues:

1. **Broken GitHub Pages link**: `https://opensite-ai.github.io/opensite-skills` — this site does not exist. Remove or replace with the actual GitHub repo URL.
2. **Unverified Discord link**: `https://discord.gg/opensite` — should be verified before publication or removed.
3. **Incorrect changelog date**: `### 1.0.0 (2024-11-15)` — this skill was created in March 2026, not November 2024.
4. **Fabricated metrics**: `Lines of Code: 24,387` is clearly incorrect for a skill with a ~16KB SKILL.md and ~10KB of Python scripts. Remove the metrics section entirely or replace with accurate file counts.
5. **Incorrect installation step**: `pip install -r requirements.txt` — there is no `requirements.txt` because the scripts use only Python stdlib. Remove this line or add a `requirements.txt` with a comment clarifying no external dependencies are needed.

---

### 🔵 LOW — Nice to have for v1.0 public release

#### LOW-1: Missing template files referenced in SKILL.md

SKILL.md references `OBSERVATIONS.md` and the session handoff format inline, but the `templates/` directory only contains `change-manifest.md`. Three additional templates would significantly improve the out-of-box contributor experience:

| Missing file | Content |
|---|---|
| `templates/observations.md` | OBSERVATIONS.md format with severity table and example entries |
| `templates/session-handoff.md` | `.refactor-session.md` format with all fields pre-labeled |
| `templates/refactor-scope-allowlist.example` | An example allowlist with comments explaining glob and directory patterns |

---

#### LOW-2: `agents/openai.yaml` is under-specified

**File:** `large-scale-refactor/agents/openai.yaml`

Current file has 23 lines and is missing machine-readable versions of the core guardrail parameters. Extending this file enables platforms that support machine-parseable skill configs to apply the circuit-breaker and budget constraints without relying solely on the prose in SKILL.md.

**Additions to make:**

```yaml
# Add these blocks to agents/openai.yaml
circuit_breaker:
  soft_threshold: 20   # agent receives nudge
  hard_threshold: 40   # agent must halt and output

file_budget_defaults:
  low_risk: 200
  medium_risk: 50
  high_risk: 20

human_checkpoint_triggers:
  - spec_gate
  - drift_check_failure
  - out_of_scope_file
  - new_dependency_required
  - new_abstraction_required
  - unexpected_test_failure
  - file_budget_reached
  - spec_ambiguity
```

---

#### LOW-3: `IMPLEMENTATION_SUMMARY.md` should not be in the public skill directory

**File:** `large-scale-refactor/IMPLEMENTATION_SUMMARY.md`

This is an internal build artifact that documents the development process, not a user-facing document. In a public open source repo it adds noise and confusion ("what is this file?"). Move to `.ctx/` or delete before the public release announcement.

---

#### LOW-4: Pilot batch guidance belongs in SKILL.md, not only in README

The README states "Begin with a pilot of 10-20 files to validate approach" as a best practice, but this guidance is absent from the normative SKILL.md. First-time users who only read SKILL.md (the standard entry point) won't see this critical recommendation.

**Add to § 3.1 as a note:**

```markdown
> **Pilot Batch Recommendation**: For any new refactor task, process the first
> batch with only 10-20 files — even if the risk level would normally allow more.
> This surfaces edge cases in the spec, validates the transformation approach, and
> lets you refine patterns before scaling. Do not skip the pilot batch.
```

---

#### LOW-5: No `CONTRIBUTING.md` or `good-first-issue` guidance

For an open source skill library intended to receive community contributions, there is no contribution guide. The README has a 5-line "Contributing" section but no `CONTRIBUTING.md` at the repo level. This is a common expectation for discoverable open source projects.

**Minimum viable `CONTRIBUTING.md` additions:**
- How to propose a new skill (issue template)
- Skill quality checklist (mirrors the Agent Skills authoring checklist from the open standard)
- How to improve an existing skill
- How to run the test suite locally
- PR conventions

---

## Enhancement Opportunities (Post-v1)

These are not blocking issues but represent high-value improvements for a future `1.1.0`:

| ID | Enhancement | Value |
|----|------------|-------|
| ENH-1 | `verify_scope.py --github-actions` flag that outputs GitHub Actions annotation format | Makes the script drop-in for any CI workflow |
| ENH-2 | Add note to § 6 about using the `memory` / `memory-write` skill as the persistence layer | Bridges the session handoff file to the existing memory skill ecosystem |
| ENH-3 | Negative activation guards — patterns where skill should NOT trigger (single-file edits, < 5 files) | Prevents skill overhead on trivial tasks |
| ENH-4 | Rust and Rails language-specific example files in `examples/` | Aligns with OpenSite's primary stack and broadens language coverage |
| ENH-5 | `CHANGELOG.md` at the skill level | Standard open source hygiene, helps contributors understand evolution |
| ENH-6 | GitHub Actions workflow file for automated scope verification on PRs | Demonstrates the skill's own tooling in action |

---

## Prioritized Fix Checklist

Use this as your PR checklist for the pre-release cleanup:

### Blocker (must merge before announcement)
- [ ] **CRIT-1** — Fix hardcoded paths in `test_verify_scope.py`
- [ ] **HIGH-3** — Delete `SKILL.md.bak`

### High priority (should merge before announcement)
- [ ] **HIGH-1** — Fix `verify_scope.py` pattern matching with `fnmatch`
- [ ] **HIGH-2** — Fix `generate_allowlist.py` directory regex
- [ ] **MED-1** — Restore rich frontmatter to `SKILL.md` (merge from `.bak` before deleting)
- [ ] **MED-2** — Add § 6.2 (context flushing) and § 2.5 (50-line threshold) to `SKILL.md`
- [ ] **MED-3** — Fix README broken links, wrong date, fabricated metrics, bad install step

### Nice to have for v1.0
- [ ] **LOW-1** — Add `templates/observations.md`, `templates/session-handoff.md`, `templates/refactor-scope-allowlist.example`
- [ ] **LOW-2** — Expand `agents/openai.yaml` with circuit-breaker and budget fields
- [ ] **LOW-3** — Move/remove `IMPLEMENTATION_SUMMARY.md`
- [ ] **LOW-4** — Add pilot batch note to `SKILL.md` § 3.1
- [ ] **LOW-5** — Add repo-level `CONTRIBUTING.md`

---

## What's Already Solid

The following are not findings — they are strengths worth calling out explicitly:

- **§§ 1–4 core guardrails** — The Spec Gate, Substitution Test, No Emergent Systems rule, and Dependency Lockdown together form a robust three-layer defense. The language is clear, imperative, and unambiguous. These sections require no changes.
- **Drift Detection Checkpoint (§ 3.4)** — The five-question self-audit is the right format. Short, binary, and requires explicit evidence. This is the skill's most practically useful feature for parallel/batch scenarios.
- **Checkpoint Message Format (§ 4)** — The structured ⏸ CHECKPOINT template with Options A/B/C and Recommendation is excellent. It gives agents a consistent format that humans can scan quickly.
- **Session Handoff File (§ 6.1)** — This is the most important long-running-task contribution from the Model Council. The format is correct, the fields are complete, and the "committed with each session's changes" instruction is critical.
- **`verify_scope.py` architecture** — The overall structure (read allowlist → get git diff → check compliance → report) is correct and well-organized. It only needs the pattern matching fix (HIGH-1) to be production-ready.
- **`examples/complete-workflow.md`** — The most complete and best-documented example in the skill library. The step-by-step TypeScript migration walkthrough with annotated outputs is exactly what new users need.
- **Multi-platform coverage (§ 7)** — The Qoder, Claude Code, Factory Droid/Devin, and Copilot notes are current, accurate, and specific enough to be actionable.

---

## Standards Conformance Assessment

| Standard | Requirement | Status |
|----------|-------------|--------|
| Agent Skills spec | `name` field required, 1-64 chars, lowercase | ✅ Passes |
| Agent Skills spec | `description` field required, up to 1024 chars | ✅ Passes (currently 340 chars) |
| Agent Skills spec | Directory name must match `name` field | ✅ Passes |
| Agent Skills spec | `SKILL.md` required at skill root | ✅ Passes |
| opensite-skills standard | `agents/openai.yaml` present | ✅ Passes |
| opensite-skills standard | `references/activation.md` present | ✅ Passes |
| Open source hygiene | No hardcoded local paths | ❌ Fails (CRIT-1) |
| Open source hygiene | No `.bak` files in repo | ❌ Fails (HIGH-3) |
| Open source hygiene | Working test suite | ❌ Fails (CRIT-1) |
| Open source hygiene | Accurate README | 🟡 Partial (MED-3) |
| Agent Skills spec | `license` field present | ❌ Missing (add to frontmatter) |
| opensite-skills standard | Core guardrails not subject to Codex deepening | ✅ Explicitly noted in § 7 |
