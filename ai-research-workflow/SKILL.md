---
name: ai-research-workflow
description: >
  Deep research and AI workflow orchestration patterns for Octane. Use when
  working on brand guide generation, market analysis, competitive analysis,
  content brief, or any multi-step AI research pipeline. Covers the
  WorkflowBuilder/WorkflowStep orchestration system, Anthropic dual-model
  routing (Opus for research, Sonnet for generation), and the ai_tasks
  persistence pattern.
compatibility: >
  Best in the Octane Rust repo with Anthropic workflow code and network access
  for external model or API verification.
metadata:
  opensite-category: ai
  opensite-scope: octane
  opensite-visibility: public
---
# AI Research Workflow Skill

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.
- Example: [examples/workflow-brief.example.md](examples/workflow-brief.example.md)
- Helper: `scripts/validate_workflow_brief.py`
- Template: [templates/workflow-brief.md](templates/workflow-brief.md)

## Task Focus for $ARGUMENTS
When this skill is invoked explicitly, treat `$ARGUMENTS` as the primary scope to optimize around: a repo path, component name, incident id, rollout target, or other concrete task boundary.

You are building or modifying multi-step AI research workflows in Octane (`github.com/Toastability/octane`). These workflows power the core AI services: brand guide, market analysis, competitive analysis, content brief, and SEO analysis.

## Orchestration Architecture

Workflows use the `WorkflowBuilder` in `src/services/orchestration/` and are executed by Anthropic-backed agents. Two models, two phases:

- **Phase 1 (Research)**: Opus 4.6 + web search (`context-1m-2025-08-07`, `web-search-2025-03-05`)
- **Phase 2 (Generation)**: Sonnet 4.6 + schema tools (structured output, report generation)

```rust
// Example: Market Analysis workflow
use crate::services::orchestration::{WorkflowBuilder, WorkflowStep, Agent, MemoryStore};
use std::sync::Arc;
use tokio::sync::RwLock;

pub async fn run_market_analysis(
    anthropic: Arc<AnthropicService>,
    input: MarketAnalysisInput,
) -> anyhow::Result<MarketAnalysisReport> {
    let memory = Arc::new(RwLock::new(MemoryStore::default()));

    let research_agent = Agent::new(
        "Research Agent",
        anthropic.clone(),
        AgentConfig {
            model: "claude-opus-4-6".into(),
            max_tokens: 32000,
            tools: vec!["web_search".into()],
            beta_features: vec![
                "context-1m-2025-08-07".into(),
                "web-search-2025-03-05".into(),
            ],
        },
    );

    let generation_agent = Agent::new(
        "Generation Agent",
        anthropic.clone(),
        AgentConfig {
            model: "claude-sonnet-4-6".into(),
            max_tokens: 8192,
            tools: vec!["schema_output".into()],
            beta_features: vec!["context-1m-2025-08-07".into()],
        },
    );

    let workflow = WorkflowBuilder::new("Market Analysis")
        .with_memory(memory.clone())
        .add_step(WorkflowStep::new(
            "Industry Research",
            research_agent.clone(),
            format_industry_research_prompt(&input),
        ))
        .add_parallel_steps(vec![
            WorkflowStep::new("Competitor Analysis", research_agent.clone(),
                format_competitor_prompt(&input)),
            WorkflowStep::new("Market Sizing", research_agent.clone(),
                format_market_sizing_prompt(&input)),
        ])
        .add_step(WorkflowStep::new(
            "Report Generation",
            generation_agent.clone(),
            REPORT_GENERATION_PROMPT.into(),
        ))
        .build();

    let result = workflow.execute().await?;

    // Persist result to ai_tasks table
    let report: MarketAnalysisReport = serde_json::from_value(
        result.final_output
            .ok_or_else(|| anyhow::anyhow!("Workflow produced no output"))?
    )?;

    Ok(report)
}
```

## WorkflowBuilder API

```rust
// src/services/orchestration/workflow.rs
pub struct WorkflowBuilder {
    name: String,
    steps: Vec<WorkflowStepDef>,
    memory: Option<Arc<RwLock<MemoryStore>>>,
    max_retries: u32,
    retry_delay_ms: u64,
}

impl WorkflowBuilder {
    pub fn new(name: impl Into<String>) -> Self
    pub fn with_memory(self, memory: Arc<RwLock<MemoryStore>>) -> Self
    pub fn add_step(self, step: WorkflowStep) -> Self
    pub fn add_parallel_steps(self, steps: Vec<WorkflowStep>) -> Self // Run concurrently
    pub fn with_max_retries(self, n: u32) -> Self
    pub fn build(self) -> Workflow

    // Workflow execution
    // .execute() → WorkflowResult
    //   .step_results: Vec<StepResult>
    //   .final_output: Option<serde_json::Value>
    //   .memory: MemoryStore (exported)
    //   .errors: Vec<String>
    //   .total_tokens: i64
}

pub struct WorkflowStep {
    pub name: String,
    pub agent: Arc<Agent>,
    pub prompt: String,
    pub depends_on: Vec<String>,  // Step names this step reads from memory
}
```

## Memory Store Pattern

Steps communicate via the shared `MemoryStore`. Each step writes its output; subsequent steps read it:

```rust
// src/services/orchestration/memory.rs
#[derive(Default)]
pub struct MemoryStore {
    entries: HashMap<String, serde_json::Value>,
}

impl MemoryStore {
    pub fn set(&mut self, key: impl Into<String>, value: serde_json::Value)
    pub fn get(&self, key: &str) -> Option<&serde_json::Value>
    pub fn get_as<T: DeserializeOwned>(&self, key: &str) -> anyhow::Result<T>
    pub fn to_context_string(&self) -> String  // Formats memory for prompt injection
}

// In a prompt — inject memory from previous steps:
const REPORT_GENERATION_PROMPT: &str = r#"
Based on the research completed in previous steps:
{memory_context}

Generate a comprehensive market analysis report following the output schema.
"#;
// The orchestration layer replaces {memory_context} with memory.to_context_string()
```

## Anthropic Service — Dual Model Routing

The `AnthropicService` in Octane already implements the dual-model architecture. Key methods:

```rust
// Opus 4.6 — use for research (web search + extended thinking)
anthropic.create_research_message(ResearchRequest {
    prompt: research_prompt,
    thinking_budget: Some(16000),
    web_search: true,
    max_tokens: 32000,
}).await?;

// Sonnet 4.6 — use for generation (structured output + schema tools)
anthropic.create_generation_message(GenerationRequest {
    prompt: generation_prompt,
    output_schema: Some(report_schema),
    max_tokens: 8192,
}).await?;

// Direct message — use when you need explicit model control
anthropic.create_message(CreateMessageRequest {
    model: "claude-sonnet-4-6".into(),
    messages: vec![/* ... */],
    max_tokens: 4096,
    tools: None,
    beta_features: vec![],
}).await?;
```

## ai_tasks Persistence Pattern

Every AI workflow writes its state to the `ai_tasks` table. Never skip this:

```rust
// Pattern for persisting workflow state
pub struct AiTaskRecord {
    pub id: uuid::Uuid,
    pub task_type: String,        // "market_analysis" | "brand_guide" | etc.
    pub account_id: uuid::Uuid,
    pub status: AiTaskStatus,     // Pending | Running | Completed | Failed
    pub input: serde_json::Value, // The original request (no PHI)
    pub output: Option<serde_json::Value>,
    pub error: Option<String>,
    pub tokens_used: i64,
    pub duration_ms: i64,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub completed_at: Option<chrono::DateTime<chrono::Utc>>,
}

pub async fn run_workflow_with_persistence(
    db: &DatabaseService,
    task_type: &str,
    account_id: uuid::Uuid,
    run: impl Future<Output = anyhow::Result<serde_json::Value>>,
) -> anyhow::Result<serde_json::Value> {
    let task_id = db.create_ai_task(task_type, account_id).await?;
    let start = std::time::Instant::now();

    match run.await {
        Ok(output) => {
            db.complete_ai_task(task_id, &output, start.elapsed()).await?;
            Ok(output)
        }
        Err(e) => {
            db.fail_ai_task(task_id, &e.to_string(), start.elapsed()).await?;
            Err(e)
        }
    }
}
```

## Workflow Types Reference

| Workflow | Handler File | Steps | Primary Model |
|---------|-------------|-------|---------------|
| Brand Guide | brand_guide.rs | Research → Tone → Brand → Report | Opus → Sonnet |
| Market Analysis | handlers/seo.rs (market section) | Industry → Competitors → Market → Report | Opus → Sonnet |
| Competitive Analysis | competitive_analysis.rs | Competitors → Pricing → Positioning → Report | Opus → Sonnet |
| Content Brief | content_brief.rs | Keywords → Topics → Structure → Brief | Opus → Sonnet |
| SEO Report | seo.rs | Crawl → Keywords → Backlinks → Report | Sonnet only |
| Video Insight | (Phase 1 launch) | Transcribe → Analyze → Summarize | Sonnet (vLLM) |

## Parallel Step Rules

1. Steps can only run in parallel if they don't depend on each other's memory outputs
2. Maximum 3 parallel steps per batch (to avoid context window conflicts)
3. Each parallel step gets its own memory namespace to prevent write conflicts
4. Parallel steps share the read-only input context but have isolated write namespaces

```rust
// Safe: these steps don't depend on each other
.add_parallel_steps(vec![
    WorkflowStep::new("Competitor Research", agent.clone(), competitor_prompt),
    WorkflowStep::new("Market Sizing", agent.clone(), sizing_prompt),
    WorkflowStep::new("Industry Trends", agent.clone(), trends_prompt),
])

// Unsafe: if Report Generation needs competitor data, it can't run in parallel
// It must be a sequential step after the parallel batch completes
.add_step(WorkflowStep::new("Report Generation", gen_agent, report_prompt))
```

## Token Budget Management

```rust
// Estimate token cost before running expensive workflows
pub fn estimate_workflow_tokens(workflow_type: &str) -> TokenBudget {
    match workflow_type {
        "brand_guide" => TokenBudget { research: 50_000, generation: 8_000 },
        "market_analysis" => TokenBudget { research: 80_000, generation: 12_000 },
        "competitive_analysis" => TokenBudget { research: 60_000, generation: 10_000 },
        "content_brief" => TokenBudget { research: 20_000, generation: 4_000 },
        _ => TokenBudget { research: 32_000, generation: 4_096 },
    }
}

// Check account token balance before starting
pub async fn check_token_balance(
    db: &DatabaseService,
    account_id: uuid::Uuid,
    required: i64,
) -> anyhow::Result<()> {
    let balance = db.get_token_balance(account_id).await?;
    if balance < required {
        return Err(anyhow::anyhow!(
            "Insufficient token balance: {} available, {} required",
            balance, required
        ));
    }
    Ok(())
}
```
