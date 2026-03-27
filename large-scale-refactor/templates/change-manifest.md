# Change Manifest Template

```
CHANGE MANIFEST — <subtask-id>
==============================
Task: <task-name>
Completed: <ISO datetime>
Files modified: <N>
Files created: <N> (should be 0 for pure refactors)
Files deleted: <N>

### Modified Files
| File | Change Type | Lines +/- | Notes |
|------|-------------|-----------|-------|
| src/Button.tsx | Type annotation | +12/-3 | Added Props interface |
| src/api/user.ts | Import update | +2/-2 | Changed import extension |
| src/utils/helpers.ts | Type conversion | +8/-0 | Added return types |

### Scope Compliance
- [x] All modified files were in the IN SCOPE list
- [x] No files were created outside spec-defined outputs
- [x] No dependencies were added or removed beyond spec-allowed
- [x] No new abstractions or systems were created
- [x] All drift checks passed (logs attached in drift-check-<subtask-id>.md)

### Test Results
- Before: 450 passed, 12 failed
- After: 450 passed, 12 failed
- New failures: none
- Pre-existing failures: Listed in pre-existing-failures.md

### Drift Check Log
```
DRIFT CHECK — <subtask-id>
Files touched so far: 42
Task: js-to-ts-migration

1. Does every changed file appear in the IN SCOPE list? YES
   Evidence: All files in src/components/, src/hooks/, src/utils/

2. Did I add any new files not defined in the spec? NO
   List: N/A

3. Did I add, remove, or modify any dependency? NO
   List: N/A

4. Did I make any change that fails the Substitution Test? NO
   All changes were strictly necessary for TypeScript conversion

5. Did I create any new abstraction, utility, or system? NO
   No new files or systems created
```
```
