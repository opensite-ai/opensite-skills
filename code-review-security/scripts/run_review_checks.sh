            #!/usr/bin/env bash
            set -euo pipefail

            TARGET="${1:-.}"
            if [ ! -e "$TARGET" ]; then
              echo "Target not found: $TARGET" >&2
              exit 1
            fi

            section() {
              printf '
## %s
' "$1"
            }

            run_rg() {
              local pattern="$1"
              shift
              rg -n --hidden --glob '!node_modules/**' --glob '!dist/**' --glob '!tmp/**' "$pattern" "$TARGET" "$@" || true
            }

            section "PHI and logging"
            run_rg 'tracing::(info|debug|warn)|log::info|Rails\.logger|puts\b|pp\b'

            section "Sentry and external telemetry"
            run_rg 'sentry::capture|Sentry\.capture|capture_message|capture_exception'

            section "SQL construction risks"
            run_rg 'format!\s*\(.*SELECT|format!\s*\(.*INSERT|find_by_sql\(|execute\('

            section "LLM provider usage"
            run_rg 'generate_structured|create_message|anthropic\.|AuditedLlmProvider'

            section "Unsafe Rust and auth surfaces"
            run_rg '\bunsafe\b|Router::new|\.route\(|Extension<Pool>|Extension<Arc<Pool>>'

            printf '
Review the matches manually. This helper is a triage pass, not a substitute for reasoning.
'
