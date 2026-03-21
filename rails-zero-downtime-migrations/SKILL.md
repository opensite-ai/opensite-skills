---
name: rails-zero-downtime-migrations
description: >
  Zero-downtime database migration patterns for Rails 6.1+ on PostgreSQL with
  Heroku deployments. Covers the hot-compatibility principle, concurrent index
  creation, multi-step column operations, constraint validation strategies, and
  Heroku-specific release phase coordination. Use when adding columns, indexes,
  constraints, or renaming/removing any database object on a live production
  database.
compatibility: >
  Requires Rails and PostgreSQL access plus deployment awareness;
  production-safe checks assume release-phase coordination.
metadata:
  opensite-category: data
  opensite-scope: rails
  opensite-visibility: public
---
# Rails Zero-Downtime Migrations

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.
- Template: [templates/migration-rollout.md](templates/migration-rollout.md)

## Task Focus for $ARGUMENTS
When this skill is invoked explicitly, treat `$ARGUMENTS` as the primary scope to optimize around: a repo path, component name, incident id, rollout target, or other concrete task boundary.

Every schema change on a production database is a potential outage. PostgreSQL's lock acquisition can queue requests, overflow connection pools, and bring down your application — even for operations that complete in milliseconds. This skill covers the patterns that prevent that.

---

## The Hot-Compatibility Principle

Before writing a migration, ask: **is every version of deployed application code compatible with both the old and new schema?**

A deployment rollout means old code and new code run simultaneously against the same database for some window of time. Your migration must not break either version.

```
Timeline:
  Old schema + Old code  ← safe (before migration)
  New schema + Old code  ← must be safe (migration runs, old deploys still running)
  New schema + New code  ← safe (after full deploy)
```

Operations that violate hot-compatibility:
- Dropping a column that old code still reads
- Renaming a column without updating all code references first
- Adding a `NOT NULL` column without a default (old code inserts without the column)
- Adding a `UNIQUE` constraint that rejects data old code was inserting

---

## Lock Acquisition Reference

Not all migrations take the same lock. Know what you're acquiring:

| Operation | Lock | Risk |
|-----------|------|------|
| `CREATE INDEX` (standard) | ShareLock on table | Blocks writes for the duration |
| `CREATE INDEX CONCURRENTLY` | No table lock | Safe; takes longer; can fail |
| `ADD COLUMN` with default (pre-PG12) | AccessExclusiveLock | Rewrites entire table |
| `ADD COLUMN` with default (PG12+) | AccessExclusiveLock (fast) | Does NOT rewrite table |
| `ADD COLUMN` without default | AccessExclusiveLock (instant) | Safe; always instant |
| `DROP COLUMN` | AccessExclusiveLock | Marks invisible; reclaimed at next VACUUM |
| `ADD CONSTRAINT VALIDATE` | ShareRowExclusiveLock | Blocks during validation |
| `ADD CONSTRAINT ... NOT VALID` | ShareRowExclusiveLock (brief) | Safe; validate separately |
| `VALIDATE CONSTRAINT` | ShareUpdateExclusiveLock | Does NOT block writes |

---

## Concurrent Index Creation

Never create an index without `CONCURRENTLY` on a live table larger than a few hundred rows.

```ruby
# ❌ Acquires ShareLock — blocks all writes for the duration
def change
  add_index :orders, :user_id
end

# ✅ CONCURRENTLY — no write lock, safe in production
def change
  disable_ddl_transaction!  # Required — CONCURRENTLY cannot run inside a transaction
  add_index :orders, :user_id, algorithm: :concurrently
end
```

### Why `disable_ddl_transaction!` Is Required

Rails wraps migrations in a transaction by default. PostgreSQL does not allow `CREATE INDEX CONCURRENTLY` inside a transaction. `disable_ddl_transaction!` opts the entire migration out of the transaction wrapper.

**Consequence**: if this migration fails partway through, Rails will not roll it back. You'll need to manually clean up the invalid index:

```sql
-- Check for invalid indexes after a failed concurrent build
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'orders'
  AND indexname LIKE '%invalid%';

-- Or via system catalog
SELECT schemaname, tablename, indexname
FROM pg_stat_user_indexes
WHERE NOT pg_index.indisvalid
JOIN pg_index USING (indexrelid);

-- Drop and recreate
DROP INDEX CONCURRENTLY IF EXISTS index_orders_on_user_id;
```

### Composite and Partial Indexes

```ruby
def change
  disable_ddl_transaction!

  # Composite index
  add_index :orders, [:user_id, :status], algorithm: :concurrently

  # Partial index — only index incomplete orders
  add_index :orders, :created_at,
            where: "status = 'pending'",
            algorithm: :concurrently

  # Unique index concurrently
  add_index :users, :email, unique: true, algorithm: :concurrently
end
```

---

## Adding Columns Safely

### Adding a Nullable Column (Always Safe)

```ruby
# Instant — adds column as nullable with no rewrite
def change
  add_column :products, :sku, :string
end
```

### Adding a Column with a Default (PostgreSQL 12+)

PostgreSQL 12+ stores the default in catalog metadata without rewriting rows. This is safe even on large tables.

```ruby
# Safe on PostgreSQL 12+ — no table rewrite
def change
  add_column :orders, :priority, :integer, default: 0, null: false
end
```

**If you're on PostgreSQL 11 or older**, a `NOT NULL` column with a default triggers a full table rewrite under `AccessExclusiveLock`. Use the three-step pattern:

```ruby
# Step 1: Add nullable column (instant)
def up
  add_column :orders, :priority, :integer
end

# Step 2: (separate deploy) Backfill in batches via a Rake task or console
#   Order.where(priority: nil).in_batches(of: 1000) { |b| b.update_all(priority: 0) }

# Step 3: (separate migration after backfill) Add constraint
def up
  change_column_null :orders, :priority, false
  change_column_default :orders, :priority, 0
end
```

---

## Adding NOT NULL Constraints Safely

Adding `NOT NULL` directly re-validates every existing row, holding a lock. Use the `NOT VALID` / `VALIDATE` split instead.

```ruby
# ❌ Validates all existing rows while holding ShareRowExclusiveLock
def up
  add_foreign_key :line_items, :orders
end

# ✅ Two-step: create constraint skipping validation, then validate safely
def up
  # Step 1: NOT VALID — only new/updated rows are checked; brief lock
  add_foreign_key :line_items, :orders, validate: false
end

# In a subsequent migration or release:
def up
  # Step 2: VALIDATE CONSTRAINT — acquires ShareUpdateExclusiveLock only
  # Reads rows but does NOT block writes
  validate_foreign_key :line_items, :orders
end
```

### Check Constraints

```ruby
# Same pattern for check constraints
def up
  add_check_constraint :orders, "total_cents > 0",
                        name: "orders_total_positive",
                        validate: false
end

# Separate migration to validate:
def up
  validate_check_constraint :orders, name: "orders_total_positive"
end
```

---

## Removing Columns and Tables Safely

### The Two-Step Column Removal

Removing a column while code still references it causes `ActiveRecord::StatementInvalid` or `ActiveRecord::UnknownAttributeError`. Always ignore the column before dropping it.

```ruby
# Step 1: In the first deploy — tell ActiveRecord to ignore the column
# (no migration needed for this step)
class Order < ApplicationRecord
  self.ignored_columns += %w[legacy_notes]
end

# Step 2: In a subsequent deploy — after Step 1 is stable in production
class RemoveLegacyNotesFromOrders < ActiveRecord::Migration[6.1]
  def change
    remove_column :orders, :legacy_notes, :text
  end
end
```

---

## Renaming Columns Safely

Rails' `rename_column` is a single-step operation — it doesn't give old code time to adapt. Use a four-step process:

```
Step 1: Add new column (both columns exist, old code still reads old column)
Step 2: Deploy code that writes to BOTH columns; reads from old column
Step 3: Backfill new column with existing data
Step 4: Deploy code that reads from new column; writes to new column only
Step 5: Drop old column (safely ignored by new code)
```

```ruby
# Step 1
add_column :users, :full_name, :string

# Step 3 (backfill migration — runs after Step 2 is deployed)
def up
  User.in_batches(of: 500) do |batch|
    batch.update_all("full_name = name")
  end
end

# Step 5 (after Step 4 is stable)
remove_column :users, :name, :string
```

---

## Heroku-Specific: Release Phase Migrations

Heroku's release phase runs `bundle exec rails db:migrate` before routing traffic to the new dyno. This means the migration runs while old dynos are still handling requests.

### The Release Phase Contract

- Migration runs with **old code still active on old dynos**
- New dynos start **after** migration completes
- Traffic switches **after** new dynos pass health checks

This is exactly the hot-compatibility window — your migration must be safe with old code.

### Heroku Release Phase Setup

```yaml
# Procfile
web: bundle exec puma -C config/puma.rb
release: bundle exec rails db:migrate
```

### Coordination for Multi-Step Migrations

When a migration requires multiple deploys:

```bash
# Step 1: Deploy migration only (no code changes that depend on new schema)
git push heroku step-1-add-column:main

# Wait for release phase to complete:
heroku releases --tail

# Verify migration ran:
heroku run rails db:version

# Step 2: Deploy code changes that use the new column
git push heroku step-2-use-new-column:main
```

### Avoiding Migration Timeouts

Heroku enforces a release phase timeout (varies by dyno tier, typically 10–20 minutes). Data backfills that scan large tables will exceed this limit.

```ruby
# ❌ Backfilling in a migration will time out on large tables
def up
  User.find_each { |u| u.update!(slug: u.name.parameterize) }
end

# ✅ Migrate schema only; backfill async via Rake task or Sidekiq job
def up
  add_column :users, :slug, :string
end

# In a Rake task or one-off job (run after deploy):
namespace :backfill do
  task user_slugs: :environment do
    User.where(slug: nil).in_batches(of: 500) do |batch|
      batch.each { |u| u.update_column(:slug, u.name.parameterize) }
      sleep 0.1 # be kind to the database
    end
  end
end
```

---

## Strong Migrations Gem

The `strong_migrations` gem catches unsafe migration patterns at development time:

```ruby
# Gemfile
gem "strong_migrations"
```

It will raise at `rails db:migrate` for operations like:
- Adding a column with a non-null default (on older PG)
- Creating an index without `CONCURRENTLY`
- Adding a foreign key without `validate: false`
- Calling `change_column` (which can lock the table)

When you know a migration is safe for your specific setup, use `safety_assured`:

```ruby
def change
  safety_assured do
    # Explain why this is safe in this context
    # e.g., "table has < 1000 rows in production"
    change_column :config_entries, :value, :text
  end
end
```

---

## Migration Checklist

Before every production migration:

- [ ] Does this migration pass the hot-compatibility test? (old code + new schema is safe)
- [ ] Any new index? → `algorithm: :concurrently` + `disable_ddl_transaction!`
- [ ] Any `NOT NULL` column addition? → Use `NOT VALID` + `VALIDATE` split on PG < 12
- [ ] Any column removal? → Ignore the column in Rails first (separate deploy)
- [ ] Any column rename? → Use the four-step process
- [ ] Any data backfill? → Move to a Rake task, Sidekiq job, or console; not the migration file
- [ ] Heroku release phase timeout risk? → Estimate row count × operation time
- [ ] Is the migration reversible? → Implement `up`/`down` or use `change` only when truly reversible
