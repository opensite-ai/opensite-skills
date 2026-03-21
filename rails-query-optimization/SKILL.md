---
name: rails-query-optimization
description: >
  Advanced Rails query optimization: diagnosing N+1 beyond simple includes, the
  cartesian product trap with multiple has_many eager loads, CTEs and lateral joins
  via Arel and raw SQL, reading EXPLAIN ANALYZE output, and counter cache patterns.
  Use when investigating slow Rails endpoints, optimizing ActiveRecord queries, or
  designing queries for high-traffic production endpoints.
---

# Rails Query Optimization

`includes` solves the obvious N+1. The queries that bring down production are the ones that pass review because they look fine on a small dataset. This skill covers what happens after `includes`.

---

## Reading `EXPLAIN ANALYZE` Output

Before optimizing any query, run `EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)` and read it correctly. Never guess; measure.

```ruby
# In Rails console
sql = User.joins(:orders).where(orders: { status: "pending" }).to_sql
puts ActiveRecord::Base.connection.execute("EXPLAIN (ANALYZE, BUFFERS) #{sql}").to_a.map { |r| r["QUERY PLAN"] }.join("\n")
```

### Key Nodes to Identify

| Node | What It Means |
|------|---------------|
| `Seq Scan` | Reading every row — check if an index should exist |
| `Index Scan` | Using an index; `rows=` should be close to actual rows |
| `Index Only Scan` | All needed columns are in the index — ideal |
| `Nested Loop` | Good for small outer sets; dangerous for large sets |
| `Hash Join` | Good for large sets joining on equality |
| `Sort` | Is there an index that covers this ORDER BY? |
| `Bitmap Heap Scan` | Multiple index conditions combined |

### Cost and Rows Estimation

```
Seq Scan on orders  (cost=0.00..4823.41 rows=100 width=8) (actual time=0.012..18.423 rows=9823 loops=1)
```

- `cost`: planner's estimate (startup_cost..total_cost)
- `rows=100` (estimated) vs `rows=9823` (actual) → statistics are stale; run `ANALYZE orders`
- `actual time` in milliseconds per loop
- `loops=N` × `actual time` = true total time for that node

A large discrepancy between estimated and actual rows is the primary indicator of stale statistics causing bad query plans.

---

## N+1 Detection and Resolution

### Beyond `.includes`: When It Doesn't Work

`.includes` loads the association in a second query. It does NOT work when:

1. The association is referenced in a conditional (not just a render loop)
2. The query uses `.joins` (not `.includes`) and then calls the association
3. The association is accessed through a scope that adds conditions

```ruby
# ❌ N+1 — includes won't fire because we're using .joins
restaurants = Restaurant.joins(:reviews).where(reviews: { rating: 5 })
restaurants.each { |r| r.owner.name } # N queries for owner — not included

# ✅ Include the association you actually access
restaurants = Restaurant.joins(:reviews)
                        .includes(:owner)
                        .where(reviews: { rating: 5 })
```

### Bulletproof N+1 Detection

Use the `bullet` gem in development and test:

```ruby
# config/environments/development.rb
config.after_initialize do
  Bullet.enable = true
  Bullet.rails_logger = true
  Bullet.raise = false          # Don't raise; just log while developing
  Bullet.unused_eager_loading_alert = true  # Catch over-eager includes too
end

# config/environments/test.rb
config.after_initialize do
  Bullet.enable = true
  Bullet.raise = true           # Fail the test on N+1
end
```

### `select` to Minimize Data Transfer

Even a perfect join can be slow if it selects all columns from wide tables:

```ruby
# ❌ Loads all columns including large text/JSON columns
User.joins(:profile).where(active: true)

# ✅ Select only what you need
User.joins(:profile)
    .where(active: true)
    .select("users.id, users.email, profiles.display_name, profiles.avatar_url")
```

---

## The Cartesian Product Trap

Eager loading multiple `has_many` associations with `.includes` on the same query generates a `LEFT OUTER JOIN` that multiplies rows:

```ruby
# ❌ Cartesian explosion — 500 orders × 50 reviews = 25,000 rows fetched
Restaurant.includes(:orders, :reviews).limit(10)
```

Rails deduplicates this via Ruby, but the database still transfers the full product across the network.

### Diagnosis

Enable query logging in development and watch for queries returning far more rows than expected, or using `LIMIT / OFFSET` in unexpected places.

### Fix: Separate Queries with `preload`

```ruby
# ✅ preload forces separate queries regardless — no JOIN, no cartesian product
Restaurant.preload(:orders, :reviews).limit(10)

# This fires:
#   SELECT * FROM restaurants LIMIT 10
#   SELECT * FROM orders WHERE restaurant_id IN (1,2,3,...)
#   SELECT * FROM reviews WHERE restaurant_id IN (1,2,3,...)
```

**`preload` vs `includes` vs `eager_load`:**

| Method | Behavior | Use When |
|--------|----------|----------|
| `preload` | Always separate queries | Multiple `has_many`; no WHERE on associations |
| `includes` | Rails decides (usually `preload`) | General use; switches to `eager_load` if conditions reference associations |
| `eager_load` | Always LEFT OUTER JOIN | Need to `where`/`order` on associated columns |

---

## CTEs for Complex Queries

Common Table Expressions (CTEs) make complex multi-step queries readable and allow query reuse within a single statement. Use the `activerecord-cte` gem or raw SQL.

### With `activerecord-cte` Gem

```ruby
# Gemfile: gem "activerecord-cte"

# Find restaurants whose 30-day review average is above the city average
Restaurant.with(
  city_averages: Review.select("city_id, AVG(rating) as avg_rating").group(:city_id),
  recent_reviews: Review.where("created_at > ?", 30.days.ago)
                        .select("restaurant_id, AVG(rating) as recent_avg")
                        .group(:restaurant_id)
)
.joins("JOIN city_averages ON restaurants.city_id = city_averages.city_id")
.joins("JOIN recent_reviews ON restaurants.id = recent_reviews.restaurant_id")
.where("recent_reviews.recent_avg > city_averages.avg_rating")
```

### Raw SQL CTE via `find_by_sql`

For one-off complex queries where the ORM wrapper adds no value:

```ruby
sql = <<~SQL
  WITH ranked_orders AS (
    SELECT
      restaurant_id,
      SUM(total_cents) as total_revenue,
      COUNT(*) as order_count,
      RANK() OVER (PARTITION BY city_id ORDER BY SUM(total_cents) DESC) as city_rank
    FROM orders
    WHERE created_at >= :start_date
    GROUP BY restaurant_id, city_id
  )
  SELECT r.*, ro.total_revenue, ro.order_count, ro.city_rank
  FROM restaurants r
  JOIN ranked_orders ro ON r.id = ro.restaurant_id
  WHERE ro.city_rank <= 3
SQL

restaurants = Restaurant.find_by_sql([sql, start_date: 30.days.ago])
```

---

## Lateral Joins for "Latest N per Group" Queries

The classic "get the latest order per restaurant" query is a window function problem that naive Rails code solves with N+1. Lateral joins solve this in a single query.

```ruby
# ❌ N+1 or suboptimal GROUP BY
restaurants.each { |r| r.orders.order(created_at: :desc).first }

# ✅ LATERAL join — single query, correct even with ties
sql = <<~SQL
  SELECT restaurants.*, latest.id as latest_order_id, latest.created_at as latest_order_at
  FROM restaurants
  CROSS JOIN LATERAL (
    SELECT id, created_at
    FROM orders
    WHERE orders.restaurant_id = restaurants.id
    ORDER BY created_at DESC
    LIMIT 1
  ) latest
SQL

result = Restaurant.find_by_sql(sql)
```

### Lateral Join via Arel

```ruby
lateral_subquery = Order.where("orders.restaurant_id = restaurants.id")
                        .order(created_at: :desc)
                        .limit(1)
                        .arel
                        .lateral("latest_order")

Restaurant.joins(Arel::Nodes::CrossJoin.new(lateral_subquery))
          .select("restaurants.*, latest_order.created_at as latest_order_at")
```

---

## Counter Caches

Counting associated records with `.count` fires a `SELECT COUNT(*)` query every time. For frequently-read counts, maintain a counter cache column.

```ruby
# Migration
add_column :restaurants, :reviews_count, :integer, default: 0, null: false

# Model
class Review < ApplicationRecord
  belongs_to :restaurant, counter_cache: true
end

# Backfill existing counts (run as a Rake task, not a migration)
Restaurant.find_each do |r|
  Restaurant.reset_counters(r.id, :reviews)
end
```

After this, `restaurant.reviews.count` reads `restaurants.reviews_count` without a query.

### Counter Cache with Scope

Rails doesn't support scoped counter caches natively. For conditional counts, use a trigger-maintained column or periodic Sidekiq refresh.

---

## Batch Processing to Avoid Memory Bloat

Loading all records into memory at once is the silent killer of background jobs:

```ruby
# ❌ Loads all 500K orders into memory
Order.where(status: :pending).each { |o| process(o) }

# ✅ find_each: loads 1000 at a time
Order.where(status: :pending).find_each(batch_size: 500) do |order|
  process(order)
end

# ✅ in_batches: operate on a Relation (for bulk updates)
Order.where(status: :pending).in_batches(of: 500) do |batch|
  batch.update_all(processed_at: Time.current)
end

# ✅ find_in_batches: yields arrays (useful when calling external APIs in bulk)
Order.where(status: :pending).find_in_batches(batch_size: 100) do |orders|
  external_api.bulk_process(orders.map(&:id))
end
```

---

## Indexes: When ActiveRecord Misses Them

### Polymorphic Association Indexes

Rails generates single-column indexes on foreign keys but often misses polymorphic associations:

```ruby
# ❌ Only indexes :commentable_type and :commentable_id separately
add_index :comments, :commentable_type
add_index :comments, :commentable_id

# ✅ Composite index for polymorphic queries
add_index :comments, [:commentable_type, :commentable_id]
```

### Covering Indexes

If a query always selects the same few columns, a covering index eliminates the heap fetch entirely:

```ruby
# Query: WHERE user_id = ? ORDER BY created_at DESC SELECT id, total_cents
# Covering index includes all selected columns
add_index :orders, [:user_id, :created_at, :id, :total_cents]
# PostgreSQL can answer this query from the index alone (Index Only Scan)
```

---

## Query Optimization Checklist

Before merging any endpoint or background job that runs queries:

- [ ] Run `EXPLAIN (ANALYZE, BUFFERS)` on the slowest query in the code path
- [ ] Check estimated vs actual row counts — large discrepancy = stale stats (`ANALYZE table_name`)
- [ ] Any `Seq Scan` on a table > 10K rows → consider an index
- [ ] Any multiple `has_many` includes on the same query → switch to `preload`
- [ ] Any `count` in a loop → counter cache or single COUNT query
- [ ] Any `.each` loading all records → `find_each` or `in_batches`
- [ ] Any "latest record per group" → lateral join or window function
- [ ] Any composite filter → is there a matching composite index?
