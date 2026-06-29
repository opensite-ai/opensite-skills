# Changelog Diff — `<dependency>` `<from>` → `<to>`

> One file (or section) per dependency. Produced in Phase 2 by reading the
> authoritative changelog/migration guide for EVERY intermediate version.
> This is the input to Phase 4 — it must be specific enough to grep and fix from.

## Sources Read
- [ ] CHANGELOG.md / release notes (versions read: `<from>` … `<to>`)
- [ ] Migration / upgrade guide:
- [ ] GitHub compare view: `/<owner>/<repo>/compare/v<from>...v<to>`

## Breaking Changes (compile-time)
| Symbol / API | Change | Old usage | New usage | Call sites to fix |
|--------------|--------|-----------|-----------|-------------------|
| | removed / renamed / signature changed | | | `grep` result |

## Behavioral Changes (no compile error — HIGH RISK)
| Area | Old behavior | New behavior | Action (audit call sites / add test) |
|------|--------------|--------------|--------------------------------------|
| | | | |

## Config / Feature-Flag Changes
- Renamed/removed feature flags, changed default features, changed build config:

## Deprecations (fix only if now an error)
-

## New Functionality (adopt ONLY if user requested)
-

## MSRV / Runtime Minimum Change
- ⬜ none — or: new minimum is `...`
