#!/usr/bin/env python3
"""Refresh skill support files and metadata across the repo."""

from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

PRIVATE_SKILLS = {
    "deploy-fly-io",
    "gpu-workers-python",
    "octane-embedding-pipeline",
    "octane-llm-engine",
    "octane-rust-axum",
    "octane-soc2-hipaa",
    "rails-api-patterns",
    "sentry-monitoring",
}

SKILL_META = {
    "agent-file-engine": {
        "display_name": "Agent File Engine",
        "category": "ops",
        "scope": "shared",
        "compatibility": (
            "Requires filesystem access to the target repository; shell access is "
            "strongly preferred for inventorying manifests, docs, tests, and "
            "existing AGENTS.md coverage."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
        "allowed_tools": "Read Grep Glob Bash",
        "custom_keys": {"context": "fork", "agent": "Explore"},
    },
    "ai-research-workflow": {
        "display_name": "AI Research Workflow",
        "category": "ai",
        "scope": "octane",
        "compatibility": (
            "Best in the Octane Rust repo with Anthropic workflow code and "
            "network access for external model or API verification."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
    },
    "ai-retrieval-patterns": {
        "display_name": "AI Retrieval Patterns",
        "category": "ai",
        "scope": "shared",
        "compatibility": (
            "Best with access to retrieval code, Milvus schemas, and benchmark "
            "notes; pgvector or Milvus access helps for live tuning validation."
        ),
        "deep_reasoning": True,
    },
    "automation-builder": {
        "display_name": "Automation Builder",
        "category": "ops",
        "scope": "shared",
        "compatibility": (
            "Requires shell access; browser flows work best with Node.js, "
            "Playwright, and a local Chrome or Brave install."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
        "allowed_tools": "Read Grep Bash",
    },
    "client-side-routing-patterns": {
        "display_name": "Client-Side Routing Patterns",
        "category": "frontend",
        "scope": "shared",
        "compatibility": (
            "Requires a JavaScript or TypeScript frontend repo; browser access "
            "helps when validating navigation behavior."
        ),
    },
    "code-review-security": {
        "display_name": "Code Review Security",
        "category": "security",
        "scope": "shared",
        "compatibility": (
            "Designed for local repo inspection with grep or bash-style search "
            "tools; review runs are read-only by default."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
        "allowed_tools": "Read Grep Glob Bash",
        "custom_keys": {"context": "fork", "agent": "Explore"},
    },
    "deploy-fly-io": {
        "display_name": "Deploy Fly.io",
        "category": "ops",
        "scope": "infra",
        "compatibility": (
            "Requires flyctl, network access to Fly.io and Tigris, and shell "
            "access; Docker access helps for image and machine debugging "
            "workflows."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
        "allowed_tools": "Read Grep Bash",
        "custom_keys": {"disable-model-invocation": True},
        "implicit_invocation": False,
    },
    "git-workflow": {
        "display_name": "Git Workflow",
        "category": "ops",
        "scope": "shared",
        "compatibility": (
            "Requires git; GitHub CLI or API access helps for PR, release, and "
            "review automation."
        ),
        "explicit_args": True,
        "allowed_tools": "Read Grep Bash",
        "custom_keys": {"disable-model-invocation": True},
        "implicit_invocation": False,
    },
    "gpu-workers-python": {
        "display_name": "GPU Workers Python",
        "category": "ai",
        "scope": "gpu-workers",
        "compatibility": (
            "Requires Python 3.11+, Docker, and optional RunPod or network access "
            "for deployment or live verification."
        ),
        "deep_reasoning": True,
    },
    "octane-embedding-pipeline": {
        "display_name": "Octane Embedding Pipeline",
        "category": "ai",
        "scope": "octane",
        "compatibility": (
            "Best in the Octane Rust repo with Milvus, BGE-M3, and Qwen "
            "integration code; optional network access helps for live service "
            "checks."
        ),
        "deep_reasoning": True,
    },
    "octane-llm-engine": {
        "display_name": "Octane LLM Engine",
        "category": "ai",
        "scope": "octane",
        "compatibility": (
            "Best in the Octane Rust repo with vLLM, BGE-M3, and Qwen service "
            "code; optional network access helps for live service checks."
        ),
        "deep_reasoning": True,
    },
    "octane-rust-axum": {
        "display_name": "Octane Rust + Axum",
        "category": "backend",
        "scope": "octane",
        "compatibility": (
            "Requires the Octane Rust workspace and cargo tooling; PostgreSQL or "
            "service access helps for end-to-end validation."
        ),
        "deep_reasoning": True,
    },
    "octane-soc2-hipaa": {
        "display_name": "Octane SOC2 + HIPAA",
        "category": "security",
        "scope": "octane",
        "compatibility": (
            "Best in the Octane Rust repo with access to auth, audit, and logging "
            "code paths; high-stakes changes should stay traceable."
        ),
        "deep_reasoning": True,
    },
    "opensite-ui-components": {
        "display_name": "OpenSite UI Components",
        "category": "frontend",
        "scope": "ui",
        "compatibility": (
            "Requires a React or TypeScript repo with Tailwind CSS v4 and the "
            "OpenSite UI package graph."
        ),
    },
    "page-speed-library": {
        "display_name": "Page-Speed Library",
        "category": "frontend",
        "scope": "ui",
        "compatibility": (
            "Requires a React or TypeScript monorepo with tsup and the page-speed "
            "package graph."
        ),
    },
    "pgvector-optimization": {
        "display_name": "pgvector Optimization",
        "category": "data",
        "scope": "shared",
        "compatibility": (
            "Requires PostgreSQL with pgvector or captured EXPLAIN output; SQL "
            "access improves tuning validation."
        ),
        "deep_reasoning": True,
    },
    "postgres-performance-engineering": {
        "display_name": "PostgreSQL Performance Engineering",
        "category": "data",
        "scope": "shared",
        "compatibility": (
            "Requires PostgreSQL access or captured EXPLAIN and pg_stat output; "
            "shell access helps with psql-based inspection."
        ),
        "deep_reasoning": True,
        "custom_keys": {"context": "fork", "agent": "Explore"},
    },
    "rails-api-patterns": {
        "display_name": "Rails API Patterns",
        "category": "backend",
        "scope": "rails",
        "compatibility": (
            "Requires Ruby 3.3, Bundler, and the Toastability Rails repos; "
            "PostgreSQL and Redis help for full verification."
        ),
    },
    "rails-query-optimization": {
        "display_name": "Rails Query Optimization",
        "category": "data",
        "scope": "rails",
        "compatibility": (
            "Requires Rails plus PostgreSQL access or captured EXPLAIN output from "
            "the target environment."
        ),
        "deep_reasoning": True,
    },
    "rails-zero-downtime-migrations": {
        "display_name": "Rails Zero-Downtime Migrations",
        "category": "data",
        "scope": "rails",
        "compatibility": (
            "Requires Rails and PostgreSQL access plus deployment awareness; "
            "production-safe checks assume release-phase coordination."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
    },
    "react-rendering-performance": {
        "display_name": "React Rendering Performance",
        "category": "frontend",
        "scope": "shared",
        "compatibility": (
            "Requires React 19+ code and, ideally, React DevTools Profiler or "
            "runtime traces for measurement."
        ),
        "deep_reasoning": True,
    },
    "rust-async-patterns": {
        "display_name": "Rust Async Patterns",
        "category": "backend",
        "scope": "shared",
        "compatibility": (
            "Requires a Rust async codebase and cargo; reproduction of compiler "
            "errors helps for targeted fixes."
        ),
        "deep_reasoning": True,
    },
    "rust-error-handling": {
        "display_name": "Rust Error Handling",
        "category": "backend",
        "scope": "shared",
        "compatibility": (
            "Requires a Rust codebase and cargo; error-chain validation benefits "
            "from local test coverage."
        ),
    },
    "semantic-ui-builder": {
        "display_name": "Semantic UI Builder",
        "category": "ai",
        "scope": "cross-stack",
        "compatibility": (
            "Best with access to Octane, Toastability/app, and @opensite/ui "
            "repositories plus structured-output JSON examples."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
    },
    "sentry-monitoring": {
        "display_name": "Sentry Monitoring",
        "category": "ops",
        "scope": "shared",
        "compatibility": (
            "Requires Sentry access or bundled monitoring tooling plus network "
            "access for live issue inspection."
        ),
        "deep_reasoning": True,
        "explicit_args": True,
        "allowed_tools": "Read Grep Bash",
        "custom_keys": {
            "user-invocable": False,
            "context": "fork",
            "agent": "Explore",
        },
    },
    "sidekiq-job-patterns": {
        "display_name": "Sidekiq Job Patterns",
        "category": "backend",
        "scope": "rails",
        "compatibility": (
            "Requires Ruby, Bundler, and the target Sidekiq version; "
            "version-specific docs should be loaded before coding."
        ),
        "deep_reasoning": True,
    },
    "tailwind4-shadcn": {
        "display_name": "Tailwind 4 + ShadCN",
        "category": "frontend",
        "scope": "ui",
        "compatibility": (
            "Requires Tailwind CSS v4, Node.js, and a React or Next.js codebase "
            "using the ShadCN stack."
        ),
    },
}

RESOURCE_CONTENT = {
    "ai-research-workflow": {
        "templates/workflow-brief.md": textwrap.dedent(
            """\
            # Workflow Brief

            ## Problem
            - What user-facing workflow is being added or changed?
            - Which repo paths own the orchestration logic?

            ## Inputs and Context
            - Input schema or request body
            - External dependencies and APIs
            - Existing ai_tasks or persistence requirements

            ## Step Plan
            1. Research phase
            2. Generation phase
            3. Persistence and status updates
            4. Verification

            ## Output Contract
            - Final schema
            - Error states
            - Logging and audit requirements

            ## Risks
            - Model routing regressions
            - Missing retries or status transitions
            - Storage or schema drift
            """
        ),
        "examples/workflow-brief.example.md": textwrap.dedent(
            """\
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
            """
        ),
        "scripts/validate_workflow_brief.py": textwrap.dedent(
            """\
            #!/usr/bin/env python3
            \"\"\"Validate that a workflow brief markdown file includes the required headings.\"\"\"

            from pathlib import Path
            import sys

            REQUIRED = [
                "## Problem",
                "## Inputs and Context",
                "## Step Plan",
                "## Output Contract",
                "## Risks",
            ]


            def main() -> int:
                if len(sys.argv) != 2:
                    print("Usage: validate_workflow_brief.py <brief.md>")
                    return 1

                path = Path(sys.argv[1])
                if not path.exists():
                    print(f"File not found: {path}")
                    return 1

                text = path.read_text()
                missing = [heading for heading in REQUIRED if heading not in text]
                if missing:
                    print("Missing headings:")
                    for heading in missing:
                        print(f"  - {heading}")
                    return 1

                print("Workflow brief looks structurally complete.")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
    },
    "ai-retrieval-patterns": {
        "templates/retrieval-decision-record.md": textwrap.dedent(
            """\
            # Retrieval Decision Record

            ## Corpus Shape
            - Document types
            - Language mix
            - Typical query patterns

            ## Chosen Retrieval Strategy
            - Vector RAG, PageIndex, or hybrid
            - Embedding model and why

            ## Index and Storage Design
            - Collection or index layout
            - Chunking or structural preservation strategy
            - Filters and metadata fields

            ## Evaluation Plan
            - Precision and recall expectations
            - Benchmark or golden-set checks
            - Failure modes to test

            ## Rollout Risks
            - Migration cost
            - Re-indexing implications
            - Latency or memory concerns
            """
        ),
    },
    "octane-embedding-pipeline": {
        "milvus-deployment.md": textwrap.dedent(
            """\
            # Milvus Deployment Notes

            - Keep Milvus on the Fly.io private network and align version changes with the embedding providers.
            - Verify collection names, partition strategy, and backup policy before reindexing.
            - After deploys, run a smoke test that inserts and queries a small vector batch against the target collection.
            """
        ),
        "reindex-strategy.md": textwrap.dedent(
            """\
            # Reindex Strategy

            1. Create a parallel collection for the new embedding model or dimensionality.
            2. Backfill in batches with idempotent checkpoints.
            3. Compare recall and latency against a golden query set.
            4. Switch read traffic only after the new collection reaches parity.
            5. Keep the old collection until rollback risk is negligible.
            """
        ),
    },
    "automation-builder": {
        "templates/automation-plan.md": textwrap.dedent(
            """\
            # Automation Plan

            ## Objective
            - What must the automation accomplish?
            - What is the exit condition?

            ## Tool Choice
            - API, shell, headless browser, or real browser
            - Why this is the lowest-friction option

            ## Auth and Session Handling
            - Cookie or token source
            - Expiry detection and recovery plan

            ## Page Signals
            - Load readiness signals
            - Success and failure signals
            - Modal or dialog handling

            ## Failure Recovery
            - Screenshot strategy
            - Retry boundaries
            - When to bail out and require human input
            """
        ),
        "references/media-tooling.md": textwrap.dedent(
            """\
            # Media Tooling Reference

            ## ffmpeg

            Use for transcoding, thumbnails, clip trimming, and audio extraction.

            ```bash
            # Extract thumbnail at 5 seconds
            ffmpeg -i input.mp4 -ss 00:00:05 -frames:v 1 thumbnail.jpg

            # Convert to web-optimized H.264
            ffmpeg -i input.mov \\
              -c:v libx264 -crf 23 -preset fast \\
              -c:a aac -b:a 128k \\
              -movflags +faststart \\
              output.mp4

            # Batch convert .mov -> .mp4
            for f in *.mov; do
              ffmpeg -i "$f" -c:v libx264 -crf 23 -preset fast "${f%.mov}.mp4"
            done

            # Extract audio
            ffmpeg -i input.mp4 -q:a 0 -map a output.mp3
            ```

            ## ImageMagick

            Use for bulk format conversion, compositing, overlays, color operations, and PDF rasterization.

            ```bash
            # Resize all JPEGs to max 1200px wide, in-place
            mogrify -resize '1200x>' -quality 85 *.jpg

            # Convert PNG to WebP
            convert input.png -quality 80 output.webp

            # Strip EXIF metadata
            mogrify -strip *.jpg

            # Add watermark in bottom-right corner
            convert base.jpg -gravity SouthEast -geometry +10+10 watermark.png -composite output.jpg
            ```

            ## Sharp

            Use for real-time Node.js image transforms.

            ```typescript
            import sharp from "sharp";

            async function generateVariants(input: Buffer, outputDir: string): Promise<void> {
              const sizes = [
                { name: "sm", width: 640 },
                { name: "md", width: 1024 },
                { name: "lg", width: 1536 },
                { name: "full", width: 2560 },
              ];

              await Promise.all(
                sizes.flatMap(({ name, width }) => [
                  sharp(input)
                    .resize(width, null, { withoutEnlargement: true })
                    .webp({ quality: 80 })
                    .toFile(`${outputDir}/${name}.webp`),
                  sharp(input)
                    .resize(width, null, { withoutEnlargement: true })
                    .avif({ quality: 60 })
                    .toFile(`${outputDir}/${name}.avif`),
                ]),
              );
            }
            ```

            Sharp is usually the default for server-side Node.js processing. Use ImageMagick when you need richer CLI workflows or broader format support.
            """
        ),
        "scripts/check_toolchain.sh": textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            check_command() {
              local label="$1"
              local command_name="$2"
              if command -v "$command_name" >/dev/null 2>&1; then
                printf '[ok] %s -> %s\n' "$label" "$(command -v "$command_name")"
              else
                printf '[warn] %s missing (%s)\n' "$label" "$command_name"
              fi
            }

            check_path() {
              local label="$1"
              local path="$2"
              if [ -e "$path" ]; then
                printf '[ok] %s -> %s\n' "$label" "$path"
              else
                printf '[warn] %s missing (%s)\n' "$label" "$path"
              fi
            }

            check_command "Node.js" node
            check_command "npm" npm
            check_command "npx" npx
            check_command "ffmpeg" ffmpeg
            check_command "ImageMagick" magick
            check_path "Brave browser" "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
            check_path "Google Chrome" "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

            printf '\nIf browser binaries are missing, expect Cloudflare-protected flows to fail in headless mode.\n'
            """
        ),
    },
    "code-review-security": {
        "examples/finding-example.md": textwrap.dedent(
            """\
            # Example Finding

            ## [P1] Missing PHI scrubbing before error capture

            **Why it matters**
            The handler sends raw prompt text into `sentry::capture_message`, which violates the platform rule against logging user-submitted PHI or prompt content in production telemetry.

            **What to verify**
            - Confirm the prompt body can include patient or restaurant-specific identifiers.
            - Confirm the same path is reachable in production.

            **Recommended fix**
            Hash or redact the prompt before capture, and attach only request ids or safe metadata to the event.
            """
        ),
        "scripts/run_review_checks.sh": textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            TARGET="${1:-.}"
            if [ ! -e "$TARGET" ]; then
              echo "Target not found: $TARGET" >&2
              exit 1
            fi

            section() {
              printf '\n## %s\n' "$1"
            }

            run_rg() {
              local pattern="$1"
              shift
              rg -n --hidden --glob '!node_modules/**' --glob '!dist/**' --glob '!tmp/**' "$pattern" "$TARGET" "$@" || true
            }

            section "PHI and logging"
            run_rg 'tracing::(info|debug|warn)|log::info|Rails\\.logger|puts\\b|pp\\b'

            section "Sentry and external telemetry"
            run_rg 'sentry::capture|Sentry\\.capture|capture_message|capture_exception'

            section "SQL construction risks"
            run_rg 'format!\\s*\\(.*SELECT|format!\\s*\\(.*INSERT|find_by_sql\\(|execute\\('

            section "LLM provider usage"
            run_rg 'generate_structured|create_message|anthropic\\.|AuditedLlmProvider'

            section "Unsafe Rust and auth surfaces"
            run_rg '\\bunsafe\\b|Router::new|\\.route\\(|Extension<Pool>|Extension<Arc<Pool>>'

            printf '\nReview the matches manually. This helper is a triage pass, not a substitute for reasoning.\n'
            """
        ),
    },
    "deploy-fly-io": {
        "templates/deployment-runbook.md": textwrap.dedent(
            """\
            # Deployment Runbook

            ## Target
            - Fly app
            - Environment
            - Region or machine group

            ## Preconditions
            - Secrets present
            - Image or Dockerfile ready
            - Health-check expectations

            ## Rollout Steps
            1. Preflight checks
            2. Config diff review
            3. Deploy or machine update
            4. Post-deploy verification

            ## Rollback Plan
            - Previous image or release reference
            - Rollback command
            - Data migration or cache concerns

            ## Verification
            - Health endpoints
            - Logs to inspect
            - Customer-visible smoke tests
            """
        ),
        "scripts/fly_preflight.sh": textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail

            APP="${1:-}"

            if ! command -v flyctl >/dev/null 2>&1; then
              echo "flyctl is not installed." >&2
              exit 1
            fi

            echo "== flyctl auth =="
            flyctl auth whoami || {
              echo "flyctl is not authenticated." >&2
              exit 1
            }

            if [ -z "$APP" ]; then
              echo
              echo "Usage: scripts/fly_preflight.sh <fly-app-name>"
              exit 0
            fi

            echo
            echo "== fly status: $APP =="
            flyctl status -a "$APP"

            echo
            echo "== fly machines list: $APP =="
            flyctl machines list -a "$APP" || true

            echo
            echo "== fly releases: $APP =="
            flyctl releases -a "$APP" | head -20 || true
            """
        ),
    },
    "git-workflow": {
        "templates/pull-request-body.md": textwrap.dedent(
            """\
            ## Summary
            - What changed
            - Why the change was needed

            ## Validation
            - Tests run
            - Manual checks performed
            - Any unverified paths

            ## Risks
            - Deployment or migration concerns
            - Follow-up work
            """
        ),
        "scripts/make_branch_name.py": textwrap.dedent(
            """\
            #!/usr/bin/env python3
            \"\"\"Generate a branch name using the OpenSite conventions.\"\"\"

            from __future__ import annotations

            import re
            import sys

            ALLOWED = {"feature", "fix", "chore", "security", "release", "hotfix"}


            def slugify(text: str) -> str:
                slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
                return re.sub(r"-{2,}", "-", slug)


            def main() -> int:
                if len(sys.argv) < 3:
                    print("Usage: make_branch_name.py <type> <description...>")
                    return 1

                branch_type = sys.argv[1].lower()
                if branch_type not in ALLOWED:
                    print(f"Unsupported branch type: {branch_type}")
                    return 1

                description = slugify(" ".join(sys.argv[2:]))
                if not description:
                    print("Description produced an empty slug.")
                    return 1

                print(f"{branch_type}/{description}")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
        "scripts/validate_commit_message.py": textwrap.dedent(
            """\
            #!/usr/bin/env python3
            \"\"\"Validate the repo's conventional commit format.\"\"\"

            from __future__ import annotations

            import re
            import sys

            TYPES = "feat|fix|refactor|docs|test|chore|perf|style|ci|build"
            PATTERN = re.compile(rf"^({TYPES}): [A-Z][^.\\n]{{1,70}}$")


            def main() -> int:
                if len(sys.argv) != 2:
                    print('Usage: validate_commit_message.py "type: Title"')
                    return 1

                message = sys.argv[1].strip()
                if not PATTERN.match(message):
                    print("Invalid commit message.")
                    print("Expected: <type>: <Sentence case title without trailing period>")
                    return 1

                print("Commit message format looks good.")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
    },
    "octane-llm-engine": {
        "vllm-deployment.md": textwrap.dedent(
            """\
            # vLLM Deployment Guide

            - Pin the model image, tensor-parallel settings, and GPU shape before rollout.
            - Warm the model and validate the OpenAI-compatible endpoints before switching Octane traffic.
            - Cache model weights in Tigris or local volume storage to avoid cold-start regressions.
            - Monitor token throughput, queue time, and OOM signals during the first production deploy.
            """
        ),
    },
    "octane-rust-axum": {
        "templates/endpoint-brief.md": textwrap.dedent(
            """\
            # Endpoint Brief

            ## Route Contract
            - Method and path
            - Request and response schema
            - Auth requirements

            ## State and Services
            - Typed handler state
            - Service objects involved
            - Database or storage dependencies

            ## Error Handling
            - `AppError` variants
            - Validation failures
            - Logging and tracing requirements

            ## Verification
            - Unit or integration tests
            - Curl or API smoke checks
            """
        ),
    },
    "opensite-ui-components": {
        "templates/component-brief.md": textwrap.dedent(
            """\
            # Component Brief

            ## Goal
            - What user-facing problem does the component solve?
            - Which existing components or patterns should it align with?

            ## API
            - Props
            - Variants
            - Composition points

            ## Styling
            - Required CSS variables
            - Motion or interaction details
            - Accessibility constraints

            ## Verification
            - Story or showcase update
            - Visual regression or manual checks
            """
        ),
    },
    "page-speed-library": {
        "templates/package-change-brief.md": textwrap.dedent(
            """\
            # Package Change Brief

            ## Package Scope
            - Package name
            - Consumer packages affected

            ## API Changes
            - New exports
            - Breaking changes
            - Peer dependency impact

            ## Build and Packaging
            - tsup or bundling updates
            - External dependencies
            - Tree-shaking considerations

            ## Verification
            - Build command
            - Consumer smoke test
            - Documentation or showcase updates
            """
        ),
    },
    "pgvector-optimization": {
        "templates/index-tuning-record.md": textwrap.dedent(
            """\
            # Index Tuning Record

            ## Workload
            - Query pattern
            - Filters applied
            - Collection size and embedding dimensionality

            ## Current Settings
            - Index type
            - HNSW or IVFFlat parameters
            - Search-time settings

            ## Proposed Changes
            - Parameter updates
            - Quantization or dimensionality changes
            - Expected recall and latency impact

            ## Validation
            - Recall comparison method
            - Memory measurement
            - Rollback criteria
            """
        ),
    },
    "postgres-performance-engineering": {
        "templates/explain-review.md": textwrap.dedent(
            """\
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
            """
        ),
    },
    "rails-api-patterns": {
        "templates/api-change-plan.md": textwrap.dedent(
            """\
            # API Change Plan

            ## Surface Area
            - Controller, service, or model paths
            - Routes or function endpoints involved

            ## Data Model Impact
            - Existing schema dependencies
            - Sync steps if `dashtrack-ai` is involved

            ## Behavior Changes
            - Request contract
            - Background jobs or external integrations
            - Authorization implications

            ## Verification
            - RSpec targets
            - Manual smoke checks
            - Rollout notes
            """
        ),
    },
    "rails-zero-downtime-migrations": {
        "templates/migration-rollout.md": textwrap.dedent(
            """\
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
            """
        ),
    },
    "react-rendering-performance": {
        "templates/profiler-session.md": textwrap.dedent(
            """\
            # Profiler Session

            ## Scenario
            - User action being measured
            - Device or browser context

            ## Evidence
            - Profiler screenshots or trace ids
            - Slow components or commits
            - CPU, network, or hydration signals

            ## Hypothesis
            - Rendering bottleneck
            - Data fetching bottleneck
            - Transition or animation bottleneck

            ## Proposed Fix
            - Code change
            - Measurement plan
            - Residual risks
            """
        ),
    },
    "semantic-ui-builder": {
        "templates/builder-brief.md": textwrap.dedent(
            """\
            # Builder Brief

            ## Prompt Shape
            - User intent
            - Content constraints
            - Layout or brand requirements

            ## Output Contract
            - `blockId`
            - `props` schema notes
            - Optional reasoning or citations

            ## Registry and Validation
            - Component registry lookups
            - Frontend rendering expectations
            - Fallback behavior

            ## Verification
            - Example prompt
            - Expected JSON shape
            - Preview rendering checks
            """
        ),
        "examples/semantic-output.json": json.dumps(
            {
                "blockId": "hero-centered",
                "props": {
                    "headline": "Neighborhood flavor with modern polish",
                    "subheadline": "A semantic hero block selected for a premium restaurant landing page.",
                    "cta": {"label": "Book a tasting", "href": "/reserve"},
                },
                "reasoning": (
                    "Selected a hero block because the request emphasized a bold "
                    "first impression and a single primary CTA."
                ),
            },
            indent=2,
        )
        + "\n",
        "scripts/validate_builder_payload.py": textwrap.dedent(
            """\
            #!/usr/bin/env python3
            \"\"\"Validate a semantic UI builder JSON payload.\"\"\"

            from __future__ import annotations

            import json
            from pathlib import Path
            import sys


            def main() -> int:
                if len(sys.argv) != 2:
                    print("Usage: validate_builder_payload.py <payload.json>")
                    return 1

                path = Path(sys.argv[1])
                if not path.exists():
                    print(f"File not found: {path}")
                    return 1

                data = json.loads(path.read_text())
                errors = []
                if not isinstance(data.get("blockId"), str) or not data["blockId"].strip():
                    errors.append("blockId must be a non-empty string")
                if not isinstance(data.get("props"), dict):
                    errors.append("props must be an object")
                reasoning = data.get("reasoning")
                if reasoning is not None and not isinstance(reasoning, str):
                    errors.append("reasoning must be a string when present")

                if errors:
                    for error in errors:
                        print(f"- {error}")
                    return 1

                print("Builder payload looks structurally valid.")
                return 0


            if __name__ == "__main__":
                raise SystemExit(main())
            """
        ),
    },
    "sentry-monitoring": {
        "templates/incident-summary.md": textwrap.dedent(
            """\
            # Incident Summary

            ## Scope
            - Service
            - Environment
            - Error class or trace

            ## What Happened
            - Symptom observed by users
            - First-seen and last-seen times
            - Error volume or affected requests

            ## Evidence
            - Key stack frames
            - Relevant tags, breadcrumbs, or custom context
            - Linked deploys or config changes

            ## Suspected Root Cause
            - Working theory
            - What still needs confirmation

            ## Next Actions
            - Immediate mitigation
            - Code or config follow-up
            - Monitoring checks after the fix
            """
        ),
    },
    "octane-soc2-hipaa": {
        "phi-patterns.md": textwrap.dedent(
            """\
            # PHI Detection Patterns

            Focus reviews on direct identifiers, prompt bodies, free-form notes, uploaded document text, and any field that can re-identify a patient or customer when combined with other context.

            Common high-risk buckets:
            - Names, emails, phone numbers, addresses, and dates of birth
            - Raw prompts, model responses, transcript bodies, and form uploads
            - Third-party payloads copied into logs, telemetry, or exception messages
            """
        ),
        "soc2-controls-checklist.md": textwrap.dedent(
            """\
            # SOC2 Controls Checklist

            - Confirm access control changes are reflected in code, review, and runbook artifacts.
            - Verify logging and alerting changes preserve redaction and audit expectations.
            - Re-run dependency and secret scanning before release sign-off.
            - Capture evidence for quarterly review: pull request, deploy record, and post-release verification.
            """
        ),
    },
    "tailwind4-shadcn": {
        "templates/theme-change-brief.md": textwrap.dedent(
            """\
            # Theme Change Brief

            ## Design Intent
            - Brand direction
            - Surfaces affected

            ## Token Changes
            - CSS variables added or changed
            - Component variants touched

            ## Regression Risks
            - Contrast or accessibility
            - Motion or layout coupling
            - Dark or light mode assumptions

            ## Verification
            - Screens or routes checked
            - Responsive behavior
            - Token diff review
            """
        ),
    },
}

MANUAL_IMPLICIT_FALSE = {"deploy-fly-io", "git-workflow"}
CUSTOM_KEY_ORDER = ("context", "agent", "disable-model-invocation", "user-invocable")


def wrap_block(key: str, value: str) -> list[str]:
    wrapped = textwrap.wrap(
        value,
        width=78,
        break_long_words=False,
        break_on_hyphens=False,
    )
    return [f"{key}: >"] + [f"  {line}" for line in wrapped]


def fmt_scalar(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    text = str(value)
    if re.fullmatch(r"[A-Za-z0-9_./:+-]+", text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def split_description(description: str) -> tuple[str, str]:
    match = re.search(r"\bUse when\b", description)
    if not match:
        return description.strip(), "the request matches this skill"
    before = description[: match.start()].strip().rstrip(".")
    after = description[match.end() :].strip().rstrip(".")
    return before, after


def make_short_description(display_name: str) -> str:
    candidates = [
        f"Help with {display_name} tasks",
        f"Guidance for {display_name}",
        f"{display_name} workflows",
    ]
    for candidate in candidates:
        if 25 <= len(candidate) <= 64:
            return candidate
    return (display_name[:56].rstrip() + " helper")[:64]


def make_default_prompt(name: str, description: str) -> str:
    _, when_text = split_description(description)
    if when_text:
        when_text = when_text[0].lower() + when_text[1:]
    else:
        when_text = "the request matches this skill"
    return f"Use ${name} when {when_text.rstrip('.')}."


def build_frontmatter(
    name: str,
    description: str,
    info: dict[str, object],
    custom_keys: dict[str, object],
    allowed_tools: str | None,
) -> str:
    lines = ["---"]
    lines.append(f"name: {name}")
    lines.extend(wrap_block("description", description))
    compatibility = info.get("compatibility")
    if compatibility:
        lines.extend(wrap_block("compatibility", str(compatibility)))
    lines.append("metadata:")
    lines.append(f"  opensite-category: {fmt_scalar(info['category'])}")
    lines.append(f"  opensite-scope: {fmt_scalar(info['scope'])}")
    visibility = "private" if name in PRIVATE_SKILLS else "public"
    lines.append(f"  opensite-visibility: {fmt_scalar(visibility)}")
    if allowed_tools:
        normalized = " ".join(allowed_tools.replace(",", " ").split())
        lines.append(f"allowed-tools: {fmt_scalar(normalized)}")
    for key in CUSTOM_KEY_ORDER:
        if key in custom_keys:
            lines.append(f"{key}: {fmt_scalar(custom_keys[key])}")
    lines.append("---")
    return "\n".join(lines)


def build_resource_section(name: str, info: dict[str, object]) -> str:
    bullets = [
        "- Activation and cross-agent notes: [references/activation.md](references/activation.md)"
    ]
    if info.get("deep_reasoning"):
        bullets.append(
            "- Use `ultrathink` or the deepest available reasoning mode before "
            "changing architecture, security, migration, or performance-critical "
            "paths."
        )
    for rel_path in sorted(RESOURCE_CONTENT.get(name, {})):
        if rel_path.startswith("references/"):
            bullets.append(f"- Reference: [{rel_path}]({rel_path})")
        elif rel_path.startswith("templates/"):
            bullets.append(f"- Template: [{rel_path}]({rel_path})")
        elif rel_path.startswith("examples/"):
            bullets.append(f"- Example: [{rel_path}]({rel_path})")
        elif rel_path.startswith("scripts/"):
            bullets.append(f"- Helper: `{rel_path}`")
    lines = ["## Skill Resources"]
    lines.extend(bullets)
    lines.append("")
    if info.get("explicit_args"):
        lines.extend(
            [
                "## Task Focus for $ARGUMENTS",
                "When this skill is invoked explicitly, treat `$ARGUMENTS` as the "
                "primary scope to optimize around: a repo path, component name, "
                "incident id, rollout target, or other concrete task boundary.",
                "",
            ]
        )
    return "\n".join(lines)


def insert_after_h1(body: str, section: str) -> str:
    if "## Skill Resources" in body:
        return body
    match = re.search(r"(^# .+?\n)", body, re.MULTILINE)
    if not match:
        return section + "\n" + body
    insert_at = match.end()
    return body[:insert_at] + "\n" + section + body[insert_at:]


def build_activation(name: str, description: str) -> str:
    what_text, when_text = split_description(description)
    default_prompt = make_default_prompt(name, description)
    return textwrap.dedent(
        f"""\
        # Activation Guide

        ## Best-Fit Tasks
        - {what_text}.
        - Best trigger phrase: {when_text}.

        ## Explicit Invocation
        - `{default_prompt}`

        ## Cross-Agent Notes
        - Start with `SKILL.md`, then load only the linked files you need.
        - The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
        """
    )


def write_text(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if executable:
        path.chmod(0o755)


def refresh_skill(skill_dir: Path) -> None:
    skill_name = skill_dir.name
    info = SKILL_META[skill_name]
    skill_path = skill_dir / "SKILL.md"
    text = skill_path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not match:
        raise RuntimeError(f"Invalid frontmatter in {skill_path}")
    frontmatter_text, body = match.groups()
    frontmatter = yaml.safe_load(frontmatter_text)
    description = " ".join(str(frontmatter["description"]).split())

    custom_keys = {}
    for key in CUSTOM_KEY_ORDER:
        if key in frontmatter:
            custom_keys[key] = frontmatter[key]
    for key, value in info.get("custom_keys", {}).items():
        custom_keys[key] = value

    allowed_tools = str(info.get("allowed_tools") or frontmatter.get("allowed-tools") or "")
    if not allowed_tools:
        allowed_tools = None

    if skill_name == "automation-builder":
        replacement = textwrap.dedent(
            """\
            ## Media Automation: Tool Selection

            Keep the main skill focused on browser, session, and upload automation. Load [references/media-tooling.md](references/media-tooling.md) only when the task also requires `ffmpeg`, ImageMagick, or Sharp examples.

            ---

            """
        )
        body = re.sub(
            r"## Media Automation: Tool Selection.*?(?=## Complete Example: Cloudflare-Protected SPA Upload)",
            replacement,
            body,
            flags=re.S,
        )

    body = insert_after_h1(body, build_resource_section(skill_name, info))
    body = body.replace("## Skill Resources\n\n-", "## Skill Resources\n-")
    body = body.replace(
        "## Task Focus for $ARGUMENTS\n\nWhen",
        "## Task Focus for $ARGUMENTS\nWhen",
    )
    frontmatter_block = build_frontmatter(
        skill_name,
        description,
        info,
        custom_keys,
        allowed_tools,
    )
    skill_path.write_text(frontmatter_block + "\n" + body.lstrip("\n"))

    default_prompt = make_default_prompt(skill_name, description)
    display_name = str(info["display_name"])
    openai_yaml = "\n".join(
        [
            "interface:",
            f"  display_name: {fmt_scalar(display_name)}",
            f"  short_description: {fmt_scalar(make_short_description(display_name))}",
            f"  default_prompt: {fmt_scalar(default_prompt)}",
            "",
            "policy:",
            f"  allow_implicit_invocation: {fmt_scalar(info.get('implicit_invocation', skill_name not in MANUAL_IMPLICIT_FALSE))}",
            "",
        ]
    )
    write_text(skill_dir / "agents" / "openai.yaml", openai_yaml)
    write_text(skill_dir / "references" / "activation.md", build_activation(skill_name, description))

    for rel_path, content in RESOURCE_CONTENT.get(skill_name, {}).items():
        write_text(
            skill_dir / rel_path,
            content,
            executable=rel_path.startswith("scripts/"),
        )


def main() -> int:
    skill_dirs = sorted(path for path in REPO_ROOT.iterdir() if (path / "SKILL.md").exists())
    for skill_dir in skill_dirs:
        refresh_skill(skill_dir)
    print(f"Updated support files for {len(skill_dirs)} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
