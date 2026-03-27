# Complete Workflow Example: JavaScript to TypeScript Migration

This example demonstrates a complete workflow using the `large-scale-refactor` skill for a JavaScript to TypeScript migration.

## Scenario

You have a React application with 120 JavaScript files that need to be migrated to TypeScript. The project structure:

```
src/
├── components/
│   ├── common/ (15 .js files)
│   ├── features/ (22 .js files)
│   └── layouts/ (8 .js files)
├── hooks/ (12 .js files)
├── utils/ (18 .js files)
└── api/ (10 .js files)
tests/
└── **/*.test.js (35 test files)
```

## Step 1: Invoke the Skill

```bash
# Using Claude Code
@large-scale-refactor js-to-ts-migration

# Using Cursor
/large-scale-refactor js-to-ts-migration

# Using Qoder Quest
# Select "Code with Spec" scenario and reference the skill
```

## Step 2: Review and Approve the Spec

The agent generates a spec like this:

```markdown
TASK SPEC
=========
**Task Name**: js-to-ts-migration
**Date**: 2024-11-15
**Initiator**: Jordan Hudgens

### What This Task Does
Convert all JavaScript files in the src/ directory to TypeScript, adding explicit type annotations while preserving all existing functionality. No logic changes, no style changes, and no dependency additions beyond @types/* packages required for type safety.

### Explicit Scope Boundary
**IN SCOPE** (agent may touch):
- [x] File types: *.js files in src/components/, src/hooks/, src/utils/, src/api/
- [x] Operations: Add TypeScript type annotations, change file extensions from .js to .ts/.tsx
- [x] Directories: src/components/, src/hooks/, src/utils/, src/api/
- [x] Test files: Convert corresponding *.test.js files to *.test.ts

**OUT OF SCOPE — DO NOT TOUCH** (agent must not modify):
- [ ] CSS/styling systems, color tokens, theme configuration
- [ ] Business logic, algorithms, or data transformation behavior
- [ ] Component structure beyond what is required by the task
- [ ] package.json dependencies (beyond @types/* for TS migrations)
- [ ] Build configs (webpack, babel, etc.)
- [ ] CI/CD files, deployment configs
- [ ] Files in: node_modules/, config/, scripts/, public/
- [ ] Any file not explicitly listed in IN SCOPE above

### Task Decomposition
1. Subtask A — Convert src/components/common/ — affects 15 files
2. Subtask B — Convert src/components/features/ — affects 22 files  
3. Subtask C — Convert src/components/layouts/ — affects 8 files
4. Subtask D — Convert src/hooks/ — affects 12 files
5. Subtask E — Convert src/utils/ — affects 18 files
6. Subtask F — Convert src/api/ — affects 10 files
7. Subtask G — Convert test files — affects 35 files

### Acceptance Criteria
- [ ] All .js files in scope converted to .ts/.tsx
- [ ] All files have explicit TypeScript type annotations
- [ ] All tests pass (or failures are pre-existing and documented)
- [ ] No net-new dependencies introduced (beyond spec-allowed @types/*)
- [ ] No files outside the scope boundary were modified
- [ ] Each subtask produced a separate, reviewable commit

### Rollback Plan
- Feature branch: refactor/js-to-ts-migration
- Git revert strategy: Revert individual subtask commits if needed
- Full rollback: git checkout main && git branch -D refactor/js-to-ts-migration
```

**Human reviews and approves the spec by replying "approved"**

## Step 3: Generate Scope Allowlist

```bash
python scripts/generate_allowlist.py js-to-ts-spec.md
```

This creates `.refactor-scope-allowlist`:

```
# Refactoring Scope Allowlist
# Generated from refactoring spec
# One pattern per line
# Use # for comments

src/components/
src/hooks/
src/utils/
src/api/
*.js
*.test.js
```

## Step 4: Execute the Migration

The agent processes files in batches according to the spec:

### Batch 1: src/components/common/ (15 files)

```bash
# Agent processes 15 files
# For each file:
# 1. Add TypeScript type annotations
# 2. Change extension from .js to .tsx
# 3. Update imports

# After batch completion:
git add src/components/common/
git commit -m "refactor(subtask-a): Convert common components to TypeScript

Task: js-to-ts-migration
Files: 15 files in src/components/common/
Spec: js-to-ts-spec.md"
```

**Change Manifest for Batch 1:**

```markdown
CHANGE MANIFEST — subtask-a
==============================
Task: js-to-ts-migration
Completed: 2024-11-15T14:30:00Z
Files modified: 15
Files created: 0
Files deleted: 0

### Modified Files
| File | Change Type | Lines +/- | Notes |
|------|-------------|-----------|-------|
| src/components/common/Button.tsx | Type annotation | +12/-3 | Added Props interface |
| src/components/common/Modal.tsx | Type annotation | +18/-2 | Added component types |
... (13 more files) ...

### Scope Compliance
- [x] All modified files were in the IN SCOPE list
- [x] No files were created outside spec-defined outputs
- [x] No dependencies were added or removed beyond spec-allowed
- [x] No new abstractions or systems were created
- [x] All drift checks passed

### Test Results
- Before: 450 passed, 12 failed
- After: 450 passed, 12 failed
- New failures: none
- Pre-existing failures: Listed in pre-existing-failures.md
```

### Batch 2: src/components/features/ (22 files)

The agent continues with the next batch, following the same process.

## Step 5: Verify Scope Compliance

After each batch, run the verification script:

```bash
python scripts/verify_scope.py --strict
```

Example output:

```
=== Scope Verification ===
Allowlist: .refactor-scope-allowlist
Allowed patterns: 6
  - src/components/
  - src/hooks/
  - src/utils/
  - src/api/
  - *.js
  - *.test.js

Changed files: 15
  - src/components/common/Button.tsx
  - src/components/common/Modal.tsx
  ... (13 more files) ...

✅ All changed files are within approved scope

=== Additional Verification ===
No new files created
No dependency files changed
```

## Step 6: Monitor Progress

Check the session handoff file:

```bash
cat .refactor-session.md
```

```markdown
REFACTOR SESSION HANDOFF
========================
Task: js-to-ts-migration
Last session: 2024-11-15T15:45:00Z
Agent: claude-3-opus-20240229

### Progress
- Completed subtasks: subtask-a, subtask-b
- In-progress subtask: subtask-c, 40% complete
- Remaining subtasks: subtask-d, subtask-e, subtask-f, subtask-g

### Files Remaining
src/components/layouts/Header.js
src/components/layouts/Footer.js
src/components/layouts/Sidebar.js
... (5 more files) ...

### State to Carry Forward
- Edge case: Some components use forwardRef - require special handling
- Decision: Use .tsx extension for all React components
- Pattern: Interface naming convention: ComponentNameProps

### Active Blockers
None

### Spec Ref
js-to-ts-spec.md
```

## Step 7: Handle Checkpoints

If the agent encounters a situation requiring human input:

```markdown
⏸ CHECKPOINT — dependency_required

**Trigger**: TypeScript compilation requires @types/react
**Context**: src/components/common/Button.tsx:3:8 - Cannot find module 'react'
**Options**:
  A. Add @types/react as devDependency (recommended, in spec allowance)
  B. Skip type checking for this batch (not recommended)
  C. Abort task and preserve current state for human review

**Recommendation**: A. Add @types/react as devDependency

Awaiting instruction. No changes will be made until a response is received.
```

**Human responds with approval for option A**

## Step 8: Complete the Migration

After all batches are processed:

```bash
# Final verification
python scripts/verify_scope.py --strict

# Run full test suite
npm test

# Check TypeScript compilation
tsc --noEmit
```

## Step 9: Final Documentation

Create a summary of the completed migration:

```markdown
# TypeScript Migration Complete

## Summary
- **Task**: js-to-ts-migration
- **Duration**: 3 days (6 sessions)
- **Files Converted**: 120
- **Lines Added**: +1,245
- **Lines Removed**: -387
- **Net Change**: +858 lines

## Subtasks Completed
- [x] Subtask A: src/components/common/ (15 files)
- [x] Subtask B: src/components/features/ (22 files)
- [x] Subtask C: src/components/layouts/ (8 files)
- [x] Subtask D: src/hooks/ (12 files)
- [x] Subtask E: src/utils/ (18 files)
- [x] Subtask F: src/api/ (10 files)
- [x] Subtask G: test files (35 files)

## Dependencies Added
- @types/react@18.2.45
- @types/node@20.10.5

## Test Results
- Before: 450 passed, 12 failed
- After: 452 passed, 10 failed
- New failures: 0
- Fixed failures: 2 (unrelated to migration)

## Observations Logged
- 8 files with potential N+1 query patterns
- 3 components with inconsistent prop naming
- 5 utility functions that could benefit from memoization

## Rollback Information
All changes committed in atomic batches. Individual subtasks can be reverted using:
```bash
git revert <commit-hash>
```

Full rollback:
```bash
git checkout main
git branch -D refactor/js-to-ts-migration
```
```

## Key Benefits of Using large-scale-refactor Skill

1. **Scope Safety**: No out-of-scope files were modified
2. **Atomic Progress**: Each batch was independently reviewable and revertable
3. **Documentation**: Complete audit trail of all changes
4. **Quality Control**: Regular drift detection prevented scope creep
5. **Parallel Safety**: Clear boundaries for potential parallel execution
6. **Human Oversight**: Critical decisions required explicit approval
7. **Verification**: Automated checks ensured compliance throughout

## Lessons Learned

1. **Start with a pilot**: The first batch of 15 files helped identify edge cases
2. **Monitor early**: Close observation of the first few files caught pattern issues
3. **Document decisions**: Tracking interface naming conventions in handoff file was crucial
4. **Frequent checkpoints**: Regular scope verification prevented drift
5. **Context management**: Session handoff files enabled seamless continuation across multiple days

This workflow demonstrates how the `large-scale-refactor` skill provides enterprise-grade guardrails for complex, long-running AI coding tasks while maintaining flexibility and human oversight.
