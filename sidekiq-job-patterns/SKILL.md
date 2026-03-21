---
name: sidekiq-job-patterns
description: >
  Production-grade Sidekiq job design covering idempotency, database-level
  locking, transient vs permanent error classification, dead job management, and
  version-aware API differences across Sidekiq 6.5.x through 8.x. IMPORTANT:
  Before writing any Sidekiq job code, check the exact version in Gemfile.lock
  and load the docs via Context7 — the API changed significantly between major
  versions.
compatibility: >
  Requires Ruby, Bundler, and the target Sidekiq version; version-specific docs
  should be loaded before coding.
metadata:
  opensite-category: backend
  opensite-scope: rails
  opensite-visibility: public
---
# Sidekiq Job Patterns

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.

## Version-First Workflow

Sidekiq's API changed significantly across major versions. **Before writing any job code**, identify the exact version in `Gemfile.lock` and load the correct documentation:

```bash
# Check exact Sidekiq version
grep -i "^    sidekiq " Gemfile.lock
# e.g., "    sidekiq (7.3.2)"
```

Then load the version-specific docs via Context7 before writing any job code. API differences that will break your code if you assume the wrong version:

| Feature | Sidekiq 6.5.x | Sidekiq 7.x | Sidekiq 8.x |
|---------|--------------|-------------|-------------|
| Batch API | Sidekiq Pro | Sidekiq Pro | Sidekiq Pro |
| `Sidekiq::Worker` module | Required include | Deprecated → use `Sidekiq::Job` | Removed (use `Sidekiq::Job`) |
| Error handler registration | `Sidekiq.configure_server` | `Sidekiq.configure_server` | Changed — check docs |
| Rate limiting | `sidekiq-throttled` gem | Built-in (Pro) or gem | Check version docs |
| `perform_async` return value | `jid` String | `jid` String | `jid` String |
| Unique jobs | `sidekiq-unique-jobs` gem | `sidekiq-unique-jobs` gem | Check compatibility |

---

## Job Class Structure

```ruby
# Sidekiq 7.x+ (use Sidekiq::Job; Sidekiq::Worker still works in 7.x but deprecated)
class ProcessOrderJob
  include Sidekiq::Job

  # sidekiq_options is the correct method for 7.x+
  sidekiq_options(
    queue: :orders,
    retry: 5,
    backtrace: true,
  )

  def perform(order_id)
    # Always look up by ID — never serialize ActiveRecord objects
    # (they go stale between enqueue and execution)
    order = Order.find_by(id: order_id)
    return unless order # guard: record may have been deleted

    process_order(order)
  end
end

# Sidekiq 6.5.x (use Sidekiq::Worker)
class ProcessOrderJob
  include Sidekiq::Worker

  sidekiq_options queue: :orders, retry: 5

  def perform(order_id)
    order = Order.find_by(id: order_id)
    return unless order
    process_order(order)
  end
end
```

---

## Idempotency: The Non-Negotiable Requirement

A Sidekiq job **will** be executed more than once. Network partitions, process restarts mid-job, and retry storms all cause re-execution. Design every job to be safely re-runnable.

### Check-Then-Act Pattern

```ruby
class SendWelcomeEmailJob
  include Sidekiq::Job
  sidekiq_options retry: 3

  def perform(user_id)
    user = User.find_by(id: user_id)
    return unless user

    # Guard: don't send if already sent
    return if user.welcome_email_sent_at?

    UserMailer.welcome(user).deliver_now

    # Mark as sent AFTER successful delivery
    user.update_column(:welcome_email_sent_at, Time.current)
  end
end
```

### Idempotency Keys for External API Calls

When calling external services (payment processors, email providers), use an idempotency key so the service deduplicates on their end:

```ruby
class ChargeCustomerJob
  include Sidekiq::Job
  sidekiq_options retry: 3

  def perform(order_id)
    order = Order.find_by(id: order_id)
    return unless order
    return if order.charge_completed?

    # Use a stable, deterministic idempotency key
    # order_id alone is sufficient — retries use the same key
    idempotency_key = "charge-order-#{order_id}"

    result = PaymentGateway.charge(
      amount: order.total_cents,
      customer: order.customer_token,
      idempotency_key: idempotency_key,
    )

    order.update!(
      charge_id: result.charge_id,
      charged_at: Time.current,
    )
  end
end
```

---

## Database-Level Locking to Prevent Duplicate Execution

For jobs where two workers running simultaneously would cause data corruption, use PostgreSQL advisory locks or row-level locks — not Ruby-level mutexes.

### Advisory Locks

```ruby
class RecalculateRestaurantStatsJob
  include Sidekiq::Job
  sidekiq_options retry: 0 # Don't retry; the next scheduled run will pick it up

  LOCK_PREFIX = 123_456 # Unique prefix for this job type

  def perform(restaurant_id)
    # Attempt to acquire an advisory lock scoped to this restaurant
    # pg_try_advisory_xact_lock returns false immediately if lock is held
    locked = ActiveRecord::Base.connection.execute(
      "SELECT pg_try_advisory_xact_lock(#{LOCK_PREFIX}, #{restaurant_id})"
    ).first["pg_try_advisory_xact_lock"]

    unless locked == "t" || locked == true
      logger.info "RecalculateRestaurantStatsJob skipped: lock held for restaurant #{restaurant_id}"
      return
    end

    # Lock acquired — safe to proceed
    recalculate_stats(restaurant_id)
  end
end
```

### WITH SKIP LOCKED for Queue-Style Jobs

When multiple workers should process a queue of work items exactly once each:

```ruby
class ProcessPendingExportsJob
  include Sidekiq::Job

  def perform
    # SELECT FOR UPDATE SKIP LOCKED atomically claims rows without blocking
    Export.transaction do
      export = Export
        .where(status: :pending)
        .lock("FOR UPDATE SKIP LOCKED")
        .first

      return unless export

      export.update_column(:status, :processing)
      generate_export(export)
      export.update_column(:status, :complete)
    end
  end
end
```

---

## Error Classification: Transient vs. Permanent

Sidekiq retries all errors by default. This is wrong for permanent failures (invalid data, business rule violations) — retrying wastes resources and delays alerting.

### Classify Errors Explicitly

```ruby
# Sidekiq 7.x+ approach: use sidekiq_retries_exhausted and discard_on
class ProcessWebhookJob
  include Sidekiq::Job
  sidekiq_options retry: 5

  # Permanent errors: stop immediately, don't retry, send to dead set
  discard_on ActiveRecord::RecordInvalid do |job, error|
    Sentry.capture_exception(error, extra: { job_args: job.args })
    logger.error "Discarding job due to invalid record: #{error.message}"
  end

  # Transient network errors: Sidekiq retries automatically with backoff
  # No action needed — default retry behavior handles these

  sidekiq_retries_exhausted do |job, error|
    # Called after all retries are exhausted — job moves to Dead Set
    Sentry.capture_exception(error, extra: { job_args: job.args, exhausted: true })
    # Optionally: update database record to reflect permanent failure
    order_id = job["args"].first
    Order.find_by(id: order_id)&.update_column(:status, :failed)
  end

  def perform(order_id)
    order = Order.find(order_id) # raises RecordNotFound if deleted
    process(order)
  end
end
```

### Retry Configuration by Error Type

```ruby
# Sidekiq 6.5.x compatible approach
class SyncInventoryJob
  include Sidekiq::Worker
  sidekiq_options retry: 10

  def perform(item_id)
    item = Item.find_by(id: item_id)
    return unless item

    begin
      InventoryApi.sync(item)
    rescue InventoryApi::RateLimitError => e
      # Re-enqueue with explicit delay — not a standard retry
      # (standard retries use exponential backoff from the first failure)
      self.class.perform_in(e.retry_after.seconds, item_id)
    rescue InventoryApi::InvalidItemError
      # Permanent failure — mark it and stop
      item.update_column(:sync_status, :invalid)
      # Don't re-raise; let the job succeed (don't retry)
    end
    # Any other exception propagates and triggers Sidekiq's retry mechanism
  end
end
```

---

## `sidekiq-unique-jobs`: Deduplication

When the same logical job should not be enqueued twice for the same arguments, use `sidekiq-unique-jobs` (community gem, compatible across Sidekiq 6–8 — check current version for exact API).

```ruby
# Gemfile
# gem "sidekiq-unique-jobs"

class RebuildSearchIndexJob
  include Sidekiq::Job

  sidekiq_options(
    queue: :search,
    retry: 3,
    lock: :until_executed,       # Don't enqueue if a job with same args is pending
    lock_ttl: 1.hour.to_i,       # Lock expires after 1 hour regardless
    on_conflict: :log,           # Log conflicts instead of raising
  )

  def perform(restaurant_id)
    SearchIndex.rebuild_for(restaurant_id)
  end
end
```

**Lock strategies:**

| Strategy | Behavior |
|----------|----------|
| `:until_executing` | Lock released when execution starts (duplicates may queue up while running) |
| `:until_executed` | Lock held until job finishes |
| `:while_executing` | Unique while a job with same args is running |
| `:until_expired` | Lock held until TTL expires |

---

## Dead Set Management

When all retries are exhausted, Sidekiq moves jobs to the Dead Set (visible in Sidekiq Web UI). Dead jobs are kept for 6 months by default.

### Programmatic Dead Set Access

```ruby
# List dead jobs (Sidekiq 7.x API)
dead = Sidekiq::DeadSet.new
dead.each do |job|
  puts "#{job.klass} args=#{job.args} failed_at=#{job['failed_at']}"
end

# Retry all dead jobs
Sidekiq::DeadSet.new.retry_all

# Retry specific job by JID
dead = Sidekiq::DeadSet.new
dead.find_job("abc123def")&.retry

# Clear all dead jobs
Sidekiq::DeadSet.new.clear
```

### Monitoring Dead Set in Production

```ruby
# Add to a health check or monitoring job
class SidekiqHealthCheckJob
  include Sidekiq::Job
  sidekiq_options queue: :default

  DEAD_SET_ALERT_THRESHOLD = 100

  def perform
    dead_count = Sidekiq::DeadSet.new.size
    if dead_count > DEAD_SET_ALERT_THRESHOLD
      Sentry.capture_message(
        "Sidekiq Dead Set exceeds threshold",
        level: :warning,
        extra: { dead_count: dead_count },
      )
    end
  end
end
```

---

## Job Design Best Practices

### Small, Focused Arguments

```ruby
# ❌ Serializes entire ActiveRecord object — goes stale, large payload
ProcessOrderJob.perform_async(order.to_json)

# ❌ Multiple ID arrays create jobs that are hard to debug and retry partially
ProcessBatchJob.perform_async([1, 2, 3, 4, 5, ... , 10_000])

# ✅ Pass the minimum identifier needed; look up in the job
ProcessOrderJob.perform_async(order.id)

# ✅ For batches, enqueue one job per item (Sidekiq handles concurrency)
order_ids.each { |id| ProcessOrderJob.perform_async(id) }
```

### Logging Job Context

```ruby
def perform(order_id)
  logger.info "ProcessOrderJob starting", order_id: order_id

  order = Order.find_by(id: order_id)
  unless order
    logger.warn "ProcessOrderJob: order not found, skipping", order_id: order_id
    return
  end

  result = process_order(order)
  logger.info "ProcessOrderJob complete", order_id: order_id, result: result
rescue => e
  logger.error "ProcessOrderJob failed", order_id: order_id, error: e.message
  raise # Re-raise so Sidekiq handles retry
end
```

### Testing Jobs

```ruby
# spec/jobs/process_order_job_spec.rb
require "rails_helper"

RSpec.describe ProcessOrderJob, type: :job do
  # Test the job inline (synchronously) — not via Redis
  include ActiveJob::TestHelper if defined?(ActiveJob::TestHelper)

  it "processes a valid order" do
    order = create(:order, status: :pending)
    described_class.new.perform(order.id)
    expect(order.reload.status).to eq("processed")
  end

  it "skips deleted orders gracefully" do
    expect { described_class.new.perform(99_999) }.not_to raise_error
  end

  it "is idempotent" do
    order = create(:order, status: :pending)
    described_class.new.perform(order.id)
    described_class.new.perform(order.id) # second run
    expect(order.reload.processed_count).to eq(1) # not 2
  end
end
```

---

## Job Checklist

Before deploying a new Sidekiq job:

- [ ] Checked Gemfile.lock for exact Sidekiq version; loaded version-specific docs via Context7
- [ ] Job is idempotent — safe to run multiple times with the same args
- [ ] Job accepts an ID, not an ActiveRecord object
- [ ] Job guards against deleted records with `find_by` + early return
- [ ] Permanent errors use `discard_on` or are caught and handled
- [ ] External API calls use idempotency keys
- [ ] Any job that must not run concurrently uses DB-level locking (not Ruby mutexes)
- [ ] Data backfills use `in_batches` — never load all records into memory
- [ ] Job is tested with inline execution (no Redis dependency in specs)
