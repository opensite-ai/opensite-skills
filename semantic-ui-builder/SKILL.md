---
name: semantic-ui-builder
description: >
  OpenSite Semantic UI Builder patterns. Use when working on the AI-powered site
  builder (handlers/semantic_builder.rs, handlers/semantic_ui_agent.rs in
  Octane), the component registry service, the Toastability/app CMS dashboard's
  site builder views, or any task related to AI-driven UI generation, block
  selection, skin application, or the v0-clone-inspired builder interface.
compatibility: >
  Best with access to Octane, Toastability/app, and @opensite/ui repositories
  plus structured-output JSON examples.
metadata:
  opensite-category: ai
  opensite-scope: cross-stack
  opensite-visibility: public
---
# Semantic UI Builder Skill

## Skill Resources
- Activation and cross-agent notes: [references/activation.md](references/activation.md)
- Use `ultrathink` or the deepest available reasoning mode before changing architecture, security, migration, or performance-critical paths.
- Example: [examples/semantic-output.json](examples/semantic-output.json)
- Helper: `scripts/validate_builder_payload.py`
- Template: [templates/builder-brief.md](templates/builder-brief.md)

## Task Focus for $ARGUMENTS
When this skill is invoked explicitly, treat `$ARGUMENTS` as the primary scope to optimize around: a repo path, component name, incident id, rollout target, or other concrete task boundary.

You are working on the OpenSite Semantic UI Builder — an AI-powered site building engine. The system spans multiple repos: the Octane Rust API handles AI logic and component registry lookups; the Toastability/app CMS frontend renders the builder UI.

## System Architecture

```
User describes a website section
          ↓
CMS Frontend (Toastability/app)
  → POST /v1/semantic-ui-agent
          ↓
Octane (semantic_ui_agent.rs handler)
  → AnthropicService (structured output mode)
  → Returns: { blockId, props, reasoning }
          ↓
Component Registry (component_registry.rs)
  → Validates blockId exists
  → Returns full component schema
          ↓
CMS renders live preview using @opensite/ui block
```

## Semantic UI Agent Endpoint (Octane)

The `semantic_ui_agent.rs` handler receives natural language descriptions and returns structured block selections:

```rust
// src/handlers/semantic_ui_agent.rs
use crate::error::AppError;
use crate::services::AnthropicService;
use axum::{extract::State, Json};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Clone)]
pub struct SemanticUiAgentState {
    pub anthropic: Arc<AnthropicService>,
    pub component_registry: Arc<ComponentRegistryService>,
}

#[derive(Debug, Deserialize)]
pub struct SemanticUiAgentRequest {
    pub description: String,        // "I need a hero section with a dark background and CTA"
    pub category: Option<String>,   // "hero" | "features" | "testimonials" | etc.
    pub skin_id: Option<String>,    // The selected skin/theme
    pub site_context: SiteContext,  // Business type, industry, tone
}

#[derive(Debug, Deserialize)]
pub struct SiteContext {
    pub industry: String,           // "restaurant" | "saas" | "agency" | etc.
    pub tone: String,               // "professional" | "playful" | "luxury"
    pub existing_blocks: Vec<String>, // Already placed block IDs (for consistency)
}

#[derive(Debug, Serialize)]
pub struct SemanticUiAgentResponse {
    pub block_id: String,
    pub props: serde_json::Value,
    pub reasoning: String,
    pub alternatives: Vec<BlockAlternative>,
}

#[derive(Debug, Serialize)]
pub struct BlockAlternative {
    pub block_id: String,
    pub reasoning: String,
}

pub async fn semantic_ui_agent_handler(
    State(state): State<Arc<SemanticUiAgentState>>,
    Json(payload): Json<SemanticUiAgentRequest>,
) -> Result<Json<SemanticUiAgentResponse>, AppError> {
    // 1. Fetch available blocks for the requested category
    let available_blocks = state.component_registry
        .list_blocks_by_category(payload.category.as_deref())
        .await
        .map_err(|e| AppError::ExternalService(e.to_string()))?;

    // 2. Build the structured selection prompt
    let schema = build_block_selection_schema();
    let prompt = build_block_selection_prompt(&payload, &available_blocks);

    // 3. Call Anthropic with structured output (schema enforcement)
    let result = state.anthropic
        .create_message_with_schema(prompt, schema)
        .await
        .map_err(|e| AppError::ExternalService(e.to_string()))?;

    Ok(Json(serde_json::from_value(result)
        .map_err(|e| AppError::Serialization(e))?))
}

fn build_block_selection_schema() -> serde_json::Value {
    serde_json::json!({
        "type": "object",
        "properties": {
            "block_id": { "type": "string" },
            "props": { "type": "object" },
            "reasoning": { "type": "string", "maxLength": 300 },
            "alternatives": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "properties": {
                        "block_id": { "type": "string" },
                        "reasoning": { "type": "string" }
                    },
                    "required": ["block_id", "reasoning"]
                }
            }
        },
        "required": ["block_id", "props", "reasoning", "alternatives"]
    })
}
```

## Component Registry Service

```rust
// src/services/component_registry.rs
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockDefinition {
    pub id: String,
    pub name: String,
    pub category: String,
    pub description: String,
    pub tags: Vec<String>,
    pub schema: serde_json::Value,  // JSON Schema for props validation
    pub default_props: serde_json::Value,
}

pub struct ComponentRegistryService {
    // Blocks are loaded from the @opensite/ui registry.ts at startup
    // and cached in memory
    blocks: std::collections::HashMap<String, BlockDefinition>,
}

impl ComponentRegistryService {
    pub async fn list_blocks_by_category(&self, category: Option<&str>) -> anyhow::Result<Vec<&BlockDefinition>> {
        Ok(match category {
            Some(cat) => self.blocks.values()
                .filter(|b| b.category == cat)
                .collect(),
            None => self.blocks.values().collect(),
        })
    }

    pub async fn get_block(&self, id: &str) -> anyhow::Result<&BlockDefinition> {
        self.blocks.get(id)
            .ok_or_else(|| anyhow::anyhow!("Block '{}' not found in registry", id))
    }

    pub fn validate_props(&self, block_id: &str, props: &serde_json::Value) -> anyhow::Result<()> {
        let block = self.blocks.get(block_id)
            .ok_or_else(|| anyhow::anyhow!("Unknown block: {}", block_id))?;
        // Validate props against block.schema using jsonschema crate
        todo!("implement JSON Schema validation")
    }
}
```

## CMS Frontend Builder (Toastability/app)

The CMS uses the Vercel AI SDK to power the conversational builder UI:

```typescript
// app/builder/page.tsx (simplified)
"use client"

import { useChat } from "@ai-sdk/react"
import { ComponentPreview } from "@/components/builder/ComponentPreview"
import { BlockSelector } from "@/components/builder/BlockSelector"

export default function BuilderPage() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: "/api/semantic-ui",
  })

  return (
    <div className="grid grid-cols-[1fr_400px] h-screen">
      {/* Live preview */}
      <ComponentPreview blocks={generatedBlocks} />

      {/* Conversational interface */}
      <div className="flex flex-col h-full border-l border-border">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((m) => (
            <div key={m.id} className={cn(
              "rounded-lg p-3 text-sm",
              m.role === "assistant"
                ? "bg-muted text-foreground"
                : "bg-primary text-primary-foreground ml-auto"
            )}>
              {m.content}
            </div>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="p-4 border-t border-border">
          <input
            value={input}
            onChange={handleInputChange}
            placeholder="Describe what you want to add..."
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          />
        </form>
      </div>
    </div>
  )
}
```

## AI Builder System Prompt

When the builder AI is making block selection decisions:

```
You are an AI site builder assistant for OpenSite. Your job is to select the most 
appropriate UI block from the @opensite/ui component library based on the user's 
description and site context.

AVAILABLE BLOCKS: {block_list_with_descriptions}
SITE CONTEXT: {site_context}
EXISTING BLOCKS: {existing_block_ids}

Guidelines:
- Select blocks that match the industry tone (restaurant = warm/inviting, SaaS = clean/technical)
- Ensure visual consistency with existing blocks
- Prefer blocks with more configuration options for flexibility
- Always provide 2-3 alternatives in case the primary selection doesn't fit
- Fill default_props with contextually appropriate placeholder content

Return ONLY valid JSON matching the provided schema. No commentary outside the JSON.
```

## Semantic Builder Handler

The `semantic_builder.rs` handler handles full page generation (vs. single block):

```rust
// src/handlers/semantic_builder.rs
// Creates a full page layout by orchestrating multiple semantic_ui_agent calls
// Uses the Workflow orchestration pattern from src/services/orchestration/

pub async fn semantic_builder_handler(
    State(state): State<Arc<SemanticBuilderState>>,
    Json(payload): Json<SemanticBuilderRequest>,
) -> Result<Json<SemanticBuilderResponse>, AppError> {
    // 1. Parse page requirements from description
    // 2. Determine sections needed (hero, features, testimonials, CTA, footer)
    // 3. For each section: call semantic_ui_agent
    // 4. Validate all block IDs exist in component registry
    // 5. Return ordered array of block configurations
    todo!("implement page-level block orchestration")
}
```

## Block Categories Reference

Map from user intent → block category:

| User Intent | Category | Example Blocks |
|------------|----------|----------------|
| "top of page" | hero | hero-split-image, hero-centered-gradient-cta |
| "show features" | feature | feature-icon-grid-bordered, feature-bento-image-grid |
| "customer reviews" | testimonial | testimonials-marquee, testimonials-bento-grid |
| "pricing" | pricing | pricing-toggle-cards, pricing-comparison-table |
| "FAQ" | faq | faq-simple-accordion, faq-centered-accordion |
| "contact form" | contact | contact-card, contact-minimal |
| "blog posts" | blog | blog-grid-author-cards, blog-masonry-featured |
| "company info" | about | about-split-hero, about-mission-features |
| "footer" | footer | footer-newsletter-minimal, footer-links-grid |
| "navigation" | navbar | navbar-floating-pill, navbar-enterprise-mega |
