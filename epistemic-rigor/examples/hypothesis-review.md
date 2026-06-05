# Example: Hypothesis Review Session

This example shows the skill's Rigor Protocol applied to a real engineering
hypothesis. The agent was running with `epistemic-rigor` active.

---

## User Prompt

> My hypothesis is that the latency spike we're seeing in our Axum API is caused
> by connection pool exhaustion from the Postgres pool during peak load. I think
> we just need to increase `max_connections` in the pool config to fix it.

---

## Expected Agent Response (Rigor Protocol Applied)

### (a) Restate
Your hypothesis: high latency during peak load is caused by Postgres connection
pool exhaustion, and the fix is increasing `max_connections` in the SQLx pool
config.

### (b) Errors and Weaknesses First

**Possible misdiagnosis — the symptom matches multiple root causes:**
Connection pool exhaustion produces blocked acquire() calls that look identical
in traces to slow query latency. Before increasing pool size, confirm the
diagnosis:
```bash
# Check if requests are queuing on pool acquire vs. actual query time
# In SQLx: log pool events, look for "connection acquire timeout" vs "query slow"
RUST_LOG=sqlx::pool=debug cargo run
```

**The proposed fix may make things worse:**
Postgres has a hard limit (`max_connections` in `postgresql.conf`, default 100).
If your pool `max_connections` already approaches the server limit, increasing
it pushes the problem upstream to Postgres itself — which degrades under high
connection counts far more than under moderate ones. Check:
```sql
SELECT count(*) FROM pg_stat_activity;
SHOW max_connections;
```

**Pool exhaustion is often a symptom of slow queries, not the root cause:**
If queries are slow (missing index, N+1, lock contention), connections are held
longer, which exhausts the pool faster. Increasing pool size delays the
problem rather than fixing it. Run:
```sql
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 20;
```

**Axum worker thread count vs. pool size mismatch:**
If `tokio` is spawning more concurrent tasks than the pool can serve, the
correct fix may be bounding concurrency at the handler layer (tower's
`ConcurrencyLimit`) rather than expanding the pool.

### (c) What's Correct

The connection pool is a legitimate first place to look for this symptom, and
the diagnostic instinct is sound. If `pg_stat_activity` confirms connections
are maxed and query latency is normal, a pool size increase is the right lever.

### Recommendation

Before changing config: instrument and confirm. If it is pool exhaustion and
queries are fast, increase the pool — but stay under 80% of the Postgres
`max_connections` ceiling. If queries are slow, fix the queries first.

---

## What a Sycophantic Response Would Have Looked Like

> "That's a great hypothesis! Connection pool exhaustion is definitely a common
> cause of latency spikes. Increasing `max_connections` is a solid approach.
> You could also look into query optimization while you're at it."

This response validates the hypothesis without checking it, endorses the fix
without identifying its failure modes, and provides no actionable diagnostics.
The `epistemic-rigor` skill is designed to prevent exactly this pattern.
