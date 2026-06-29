# Upgrade Plan

> Fill this in during Phase 0–1. One row per dependency, including any
> transitive major bumps discovered in Phase 1.

## Context
- **Repo / package:**
- **Ecosystem / package manager:**
- **Baseline status (build / lint / test):** ⬜ green  ⬜ red — _must be green before starting_
- **Canonical commands** (from repo scripts / CI):
  - build: `...`
  - lint: `...`
  - test: `...`

## Dependencies

| Dependency | From (lockfile) | Target | Direct/Transitive | Risk (patch/minor/major) | Sequence | Notes |
|------------|-----------------|--------|-------------------|--------------------------|----------|-------|
| `example-pkg` | 1.2.7 | 1.4.0 | direct | minor | 1 | |
| | | | | | | |

## Conflicts Found (Phase 1)
- _None_ — or list each constraint chain: `pkg-a@X requires pkg-b <Y`, resolution: ...

## Upgrade Order
1.
2.

## Adopt-New-Functionality (only if user requested)
- ⬜ Not requested — keep diff minimal
- Requested items:
