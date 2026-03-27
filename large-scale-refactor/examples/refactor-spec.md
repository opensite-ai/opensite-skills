# Example Refactoring Spec: JavaScript to TypeScript Migration

```
TASK SPEC
=========
**Task Name**: js-to-ts-migration
**Date**: 2024-11-15
**Initiator**: Jordan Hudgens

### What This Task Does
Convert all JavaScript files in the src/ directory to TypeScript, adding explicit type annotations while preserving all existing functionality. No logic changes, no style changes, and no dependency additions beyond @types/* packages required for type safety.

### Explicit Scope Boundary
**IN SCOPE** (agent may touch):
- [x] File types: *.js files in src/components/, src/hooks/, src/utils/
- [x] Operations: Add TypeScript type annotations, change file extensions from .js to .ts/.tsx
- [x] Directories: src/components/, src/hooks/, src/utils/
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
3. Subtask C — Convert src/hooks/ — affects 8 files
4. Subtask D — Convert src/utils/ — affects 12 files
5. Subtask E — Convert test files — affects 35 files

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
