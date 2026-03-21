# Coverage Plan Example

## Repo

`utility-modules/opensite-ui`

## Root AGENTS.md should cover

- library mental model
- tree-shaking rules
- block registry behavior
- style token and Tailwind conventions
- shared verification commands

## Nested AGENTS.md should exist for

- `components/blocks/`
  - distinct JSON-serializable block props
  - semantic builder compatibility
  - registry and export-generation rules

## Nested AGENTS.md probably not needed for

- thin utility folders that inherit the same tree-shaking and styling rules without adding local constraints

## Why this is a good split

- The root file stays broadly useful across the repo.
- The nested file captures block-specific rules that would otherwise bloat the root.
- Agents touching `components/blocks/*` get the stronger local guidance automatically.
