# EXPLAIN Review

## Query Context
- Endpoint or job
- Input filters
- Data volume assumptions

## Plan Summary
- Key nodes
- Estimated vs actual rows
- Buffer hits and reads

## Suspected Bottleneck
- Planner issue, missing stats, lock contention, or I/O
- Evidence supporting the hypothesis

## Proposed Changes
- Index or schema change
- Query rewrite
- Vacuum or stats action

## Verification
- Before and after metrics
- Risk and rollback notes
