# Worked Example — JS major-version upgrade (peer-conflict case)

Shows the most common JavaScript failure mode: a peer-dependency conflict that
must be resolved by upgrading the *constraining* package, not by forcing.

> **Request:** upgrade `react-query` v4 → `@tanstack/react-query` v5 (a major
> migration that also renamed the package).

---

## Phase 0 — Detect & baseline
- Ecosystem: pnpm. `package.json` + `pnpm-lock.yaml`.
- From-version from lockfile: `react-query 4.36.1`.
- Baseline `pnpm build && pnpm lint && pnpm test` → green.

## Phase 1 — Resolve the graph (conflict first)
- `pnpm up @tanstack/react-query@5 --dry-run` (or `ncu`) to preview.
- **Peer conflict surfaced:** `@tanstack/react-query@5` requires `react >= 18`, but a sibling component library pins `react@17`.
- Resolution: do **not** pass `--force`/`--legacy-peer-deps`. Identify the minimal additional upgrade — bump the component library to its React-18-compatible major — and add it to the plan as a sequenced, first-class upgrade (its own changelog read in Phase 2).
- Sequence: component lib → React 18 → react-query v5.

## Phase 2 — Diff the changelogs
- Read the official **"Migrating to v5"** guide for react-query. Extract breaking changes into `templates/changelog-diff.md`: the package rename (`react-query` → `@tanstack/react-query`), removal of the object-form overloads (`useQuery({ queryKey, queryFn })` is now required), `cacheTime` → `gcTime` rename, `isLoading` → `isPending` semantics, etc.
- **Behavioral change to flag:** `isLoading`/`isPending` semantics differ — a compile-clean change that alters what the UI shows. Mark HIGH RISK.
- Read the component library's major changelog for its own breaking changes.

## Phase 3 — Install
- Edit `package.json`: remove `react-query`, add `@tanstack/react-query@^5`, bump `react`/`react-dom` and the component lib.
- `pnpm install`; confirm lockfile pins the intended versions and the peer warning is gone.

## Phase 4 — Apply code changes
- Grep `from 'react-query'` → rewrite imports to `@tanstack/react-query`.
- Grep `useQuery(`, `useMutation(`, `cacheTime`, `isLoading` → apply each documented v5 change at every call site.
- For the `isLoading`→`isPending` behavioral change, audit each loading-state branch and adjust; add/adjust tests.
- Build → read first error → fix → repeat.

## Phase 5 — Verify & report
- `pnpm build && pnpm lint && pnpm test` → green.
- Report: package rename, object-form migration across N hooks, `gcTime` rename, and the `isPending` behavioral caveat; plus the component-library bump that was required to clear the peer conflict.
