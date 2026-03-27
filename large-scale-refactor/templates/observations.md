# OBSERVATIONS.md — Out-of-Scope Findings Log

> **Purpose**: This file captures everything the agent noticed but did not act on.
> Log here. Never act on entries here. A human reviews this file at the end of the task.
>
> **Rule**: If you are tempted to fix, improve, or investigate something that is not
> in the approved spec — write it here and move on. The task has one job.

---

## Observations (NOT acted upon — logged for human review)

| # | File | Observation | Type | Severity | Logged at |
|---|------|-------------|------|----------|-----------|
| 1 | `src/api/user.ts` | Possible N+1 query in `fetchUsers` — each user triggers a separate `getRoles()` call | Performance | Medium | Subtask 2, file 18 |
| 2 | `src/components/Button.tsx` | Inline styles could use CSS custom properties from the design token system | Style | Low | Subtask 1, file 4 |
| 3 | `src/utils/format.ts` | `formatCurrency` does not handle negative values — returns `"$-12.00"` instead of `"-$12.00"` | Bug | High | Subtask 1, file 7 |

---

## Observation Entry Format

Copy this block to add a new observation:

```
| [N] | `path/to/file.ext` | [What you noticed — be specific] | [Bug / Performance / Style / Security / Architecture / Dependency] | [Critical / High / Medium / Low] | [Subtask N, file N] |
```

---

## Severity Guide

| Severity | Meaning | Example |
|----------|---------|---------|
| **Critical** | Active data loss, security hole, or system-breaking defect | SQL injection, auth bypass, data corruption |
| **High** | Incorrect behaviour affecting users or correctness | Wrong calculation result, silent error swallowed |
| **Medium** | Degraded performance or maintainability risk | N+1 query, unbounded loop, dead code |
| **Low** | Style inconsistency, minor improvement opportunity | Unused import, stale comment, formatting |

---

## Type Guide

| Type | Meaning |
|------|---------|
| **Bug** | Code that produces incorrect output or has unhandled error paths |
| **Performance** | Inefficient query, algorithm, or rendering pattern |
| **Security** | Potential vulnerability, exposed credential, insufficient validation |
| **Architecture** | Structural concern — coupling, abstraction boundary, module design |
| **Dependency** | Package that is outdated, unused, or could be replaced |
| **Style** | Inconsistency with the project's established conventions |
| **Debt** | Known workaround, TODO, or deferred decision that accumulates risk |

---

## What Happens to This File

1. The agent commits `OBSERVATIONS.md` with each session's changes.
2. At the end of the full task, a human reviews this file and triages entries.
3. **Critical / High** entries are typically filed as separate issues or PRs.
4. **Medium / Low** entries are batched for a future cleanup pass.
5. Nothing in this file is acted on during the current refactor task.

---

## Notes

<!-- Add any free-form notes the human should read alongside the table above. -->