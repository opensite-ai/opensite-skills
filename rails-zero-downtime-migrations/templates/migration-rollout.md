# Migration Rollout

## Change Summary
- Objects being added, changed, or removed
- Hot-compatibility assessment

## Rollout Sequence
1. Expand
2. Backfill or dual-write
3. Switch reads
4. Contract

## Operational Concerns
- Lock level
- Release-phase coordination
- Monitoring during rollout

## Rollback
- Safe rollback point
- Data cleanup required
