# Workflow Brief

## Problem
- Add a competitive analysis workflow for restaurant neighborhood comparisons.
- Own the orchestration in `src/services/orchestration/` and the task lifecycle in `ai_tasks`.

## Inputs and Context
- Request body includes restaurant id, geography, and competitor count.
- Research step uses web search plus internal restaurant data.
- Output must be persisted so the CMS can poll progress.

## Step Plan
1. Gather competitor and geographic context.
2. Run a structured research phase with web search enabled.
3. Generate the final JSON report with Sonnet.
4. Persist completion state and attach artifacts.

## Output Contract
- JSON report with market summary, competitor list, and citations.
- Failure states store retryable vs permanent error details.

## Risks
- Missing citation attribution.
- Inconsistent task-state transitions.
- Unbounded token usage during research.
