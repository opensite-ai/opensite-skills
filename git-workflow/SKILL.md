---
name: git-workflow
description: >
  Git workflow, branch conventions, PR patterns, and release management for
  OpenSite/Toastability repositories. Use when creating branches, writing commit
  messages, opening pull requests, managing monorepo packages, or coordinating
  cross-repo changes. Covers GitHub Actions CI patterns for Rust, Rails, and
  Next.js.
compatibility: >
  Requires git; GitHub CLI or API access helps for PR, release, and review
  automation.
metadata:
  opensite-category: ops
  opensite-scope: shared
  opensite-visibility: public
allowed-tools: "Read Grep Bash"
---
# Git Workflow Skill

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Helper: `scripts/make_branch_name.py`
- Helper: `scripts/validate_commit_message.py`
- Template: [templates/pull-request-body.md](templates/pull-request-body.md)

## Task Focus for $ARGUMENTS
When this skill is invoked explicitly, treat `$ARGUMENTS` as the primary scope to optimize around: a repo path, component name, incident id, rollout target, or other concrete task boundary.

You are following OpenSite/Toastability git conventions. These apply across all repos in the `opensite-ai` and `Toastability` organizations.

## Branch Naming

```
feature/{ticket-or-description}     # New features
fix/{issue-or-description}          # Bug fixes
chore/{description}                 # Maintenance, deps, tooling
security/{cve-or-description}       # Security patches
release/{version}                   # Release branches
hotfix/{description}                # Emergency production fixes
```

Examples:
```
feature/octane-llm-engine-phase1
fix/anthropic-streaming-timeout
chore/update-axum-to-0.8.2
security/scrub-phi-from-sentry
release/v1.4.0
hotfix/vllm-connection-pool-exhaustion
```

## Commit Message Format

Follow Conventional Commits:

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

Types: `feat` | `fix` | `chore` | `docs` | `refactor` | `test` | `perf` | `security`

Examples:
```
feat(llm): add vLLM provider with structured output support

Implements the VllmProvider struct with generate(), generate_structured(),
and generate_with_tools() methods. Uses xgrammar for JSON schema enforcement.

Closes #142

fix(anthropic): handle 529 rate limit with exponential backoff

Previously the service would immediately fail on 529 responses.
Now retries up to 3 times with 1s/2s/4s delays.

perf(embeddings): batch BGE-M3 requests to reduce round trips

Groups individual embed() calls into batches of 64 before sending
to the TEI sidecar, reducing HTTP overhead by 80%.

security(audit): scrub PHI patterns from Sentry before_send hook

Adds regex-based scrubbing for SSN, phone, email, and DOB patterns
in the Sentry before_send callback. No PHI should reach external services.
```

## PR Template

When creating a PR, follow this structure:

```markdown
## What
Brief description of what this PR does.

## Why
Why this change is needed — context and motivation.

## How
Key implementation decisions or approach.

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing steps (if applicable)

## Compliance (for Octane changes)
- [ ] No PHI logged anywhere in new code
- [ ] Audit logging added for new LLM calls
- [ ] New dependencies audited with `cargo audit`
- [ ] No external API calls from within Fly.io private network

## Checklist
- [ ] `cargo clippy` passes (Rust)
- [ ] `cargo fmt` applied
- [ ] `bundle exec rubocop` passes (Rails)
- [ ] `pnpm type-check` passes (TypeScript)
```

## Cross-Repo Change Process

When a change spans multiple repos (e.g., Octane API change + Rails client update):

1. Start in the **server** repo (Octane or toastability-service)
2. Open PR, get review, merge to main
3. Deploy server changes
4. Verify server change works in staging
5. Open dependent PR in **client** repo
6. Reference the server PR in the client PR description

For `@opensite/ui` changes that affect `Toastability/app`:
1. Make changes in `opensite-ai/opensite-ui`
2. Publish new version to npm: `pnpm publish --access public`
3. Update the `@opensite/ui` version in `Toastability/app/package.json`
4. Test in ui-library showcase first

## GitHub Actions: Octane (Rust)

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: octane_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy, rustfmt
      - uses: Swatinem/rust-cache@v2
      
      - name: Check formatting
        run: cargo fmt --all -- --check
        
      - name: Clippy
        run: cargo clippy --all-targets -- -D warnings
        
      - name: Security audit
        run: cargo audit
        
      - name: Tests
        run: cargo test --all
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/octane_test
          ANTHROPIC_API_KEY: ${{ secrets.TEST_ANTHROPIC_API_KEY }}
```

## GitHub Actions: Rails (toastability-service)

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v4
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.3'
          bundler-cache: true
          
      - name: Rubocop
        run: bundle exec rubocop --parallel
        
      - name: RSpec
        run: bundle exec rspec
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test
          RAILS_ENV: test
```

## Hotfix Process

For urgent production fixes:

```bash
# 1. Create hotfix branch from main
git checkout main && git pull
git checkout -b hotfix/critical-auth-bypass

# 2. Make minimal targeted fix
# 3. Test locally
# 4. Create PR to main (skip full review, get at least 1 approval)
# 5. Merge and deploy immediately
fly deploy --app octane-prod

# 6. Tag the hotfix
git tag v1.3.1-hotfix -m "Fix critical auth bypass in middleware"
git push --tags
```

## Database Migration Safety (Rails)

```bash
# Safe migration checklist for toastability-service:
# 1. Always use CONCURRENT index creation
# 2. Avoid locking columns in use
# 3. Use separate migrations for large backfills
# 4. Test rollback: rake db:migrate:down VERSION=<version>

# Example safe migration
class AddEmbeddingToReviews < ActiveRecord::Migration[6.1]
  disable_ddl_transaction!  # Required for CONCURRENT index
  
  def change
    add_column :reviews, :embedding_vector, :vector, limit: 1024
    add_index :reviews, :embedding_vector, 
              using: :hnsw,
              algorithm: :concurrently  # Non-blocking
  end
end
```
