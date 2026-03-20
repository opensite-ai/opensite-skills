---
name: code-review-security
description: Security-focused code review for OpenSite/Toastability platform. Use when reviewing PRs for security issues, auditing new API endpoints, checking for HIPAA/SOC2 compliance violations, reviewing Rust unsafe code, or scanning for injection vulnerabilities, data leakage, or auth bypasses. Auto-activates when reviewing code changes involving auth, LLM calls, user data, or external API integrations.
context: fork
agent: Explore
allowed-tools: Read, Grep, Glob, Bash
---

# Security Code Review Skill

You are performing a security-focused code review of the OpenSite/Toastability codebase. This is a read-only review — no file modifications. Focus on security, compliance, and data safety.

## Review Scope for $ARGUMENTS

Review the code at `$ARGUMENTS` for the following categories:

---

## 1. PHI / PII Data Leakage (HIPAA Critical)

Search for these patterns that could expose protected health or personal information:

```bash
# Check for PHI in log statements
grep -rn "tracing::info\|tracing::debug\|tracing::warn\|log::info\|puts\|p\b\|pp\b\|Rails.logger" $ARGUMENTS \
  | grep -i "email\|phone\|name\|address\|dob\|ssn\|password\|token"

# Check for PHI in Sentry captures
grep -rn "sentry::capture\|Sentry.capture" $ARGUMENTS

# Check for response bodies that might contain PHI
grep -rn "Json(\|json!\|render json:" $ARGUMENTS | head -30
```

**Flag as critical if:**
- Raw email, phone, SSN, or DOB appears in any `tracing::` call
- User content (prompts, responses) is logged without hashing
- Error messages include user-submitted content

---

## 2. Authentication & Authorization (SOC2 CC6)

```bash
# Check all new routes for auth middleware
grep -rn "\.route\|Router::new" $ARGUMENTS

# Check handlers for State extraction (should use typed state, not raw Pool)
grep -rn "Extension<Pool>\|Extension<Arc<Pool>>" $ARGUMENTS

# Rails: Check for missing authorization
grep -rn "def.*action\|def index\|def show\|def create" $ARGUMENTS \
  | grep -v "before_action\|authorize\|policy_scope"
```

**Flag as critical if:**
- Any route bypasses the auth middleware layer
- Rails controllers without `authorize` or `policy_scope`
- Direct database access without account scoping

---

## 3. SQL Injection

```bash
# Rust: Check for string interpolation in SQL
grep -rn "format!.*SELECT\|format!.*INSERT\|format!.*UPDATE\|format!.*DELETE" $ARGUMENTS

# Rails: Check for string interpolation in queries
grep -rn "\.where(\".*#{\|\.find_by_sql(\".*#{" $ARGUMENTS

# Check for raw SQL without parameterization
grep -rn "execute(\".*+\|execute(\".*format" $ARGUMENTS
```

**Flag if:** Any SQL string is constructed via string interpolation or concatenation rather than parameterized queries.

---

## 4. Secrets & Credential Exposure

```bash
# Check for hardcoded secrets
grep -rn "api_key\s*=\s*\"\|password\s*=\s*\"\|secret\s*=\s*\"" $ARGUMENTS \
  | grep -v "test\|spec\|example\|placeholder"

# Check for secrets in env! that should use credentials
grep -rn "ENV\[\".*KEY\"\]\|ENV\[\".*SECRET\"\]\|ENV\[\".*PASSWORD\"\]" $ARGUMENTS

# Check for secrets in error messages
grep -rn "format!.*api_key\|format!.*password\|format!.*secret" $ARGUMENTS
```

**Flag as critical if:** Any hardcoded credential, API key, or password appears in source code.

---

## 5. External HTTP Calls (Supply Chain / SSRF Risk)

```bash
# Find all new outbound HTTP calls
grep -rn "reqwest::\|Client::new\|\.get(\|\.post(" $ARGUMENTS | grep -v "test\|spec"

# Check for user-controlled URLs
grep -rn "\.get(&.*payload\.\|\.post(&.*payload\.\|\.get(&.*params\." $ARGUMENTS
```

**Flag if:**
- HTTP calls to user-supplied URLs without validation (SSRF risk)
- New external services not previously used
- Missing timeout on HTTP clients

---

## 6. Dependency Safety (Rust Cargo.toml changes)

```bash
# Check for new dependencies or version bumps
if [ -f "$ARGUMENTS/Cargo.toml" ] || [ "$ARGUMENTS" = "Cargo.toml" ]; then
  # Run cargo audit if available
  cargo audit 2>/dev/null || echo "cargo audit not available — check manually"
fi

# Check for unsafe code
grep -rn "unsafe\b" $ARGUMENTS | grep -v "test\|//.*unsafe"
```

**Flag if:**
- `unsafe` blocks without clear justification
- New dependencies with known CVEs
- Version pins removed (allowing uncontrolled updates)

---

## 7. LLM Output Trust (New for AI Codebase)

```bash
# Find places where LLM output is used without validation
grep -rn "generate_structured\|create_message\|anthropic\." $ARGUMENTS \
  -A5 | grep -E "execute\|query\|html!|raw\("
```

**Flag if:**
- LLM output is passed to SQL executor without schema validation
- LLM output is rendered as raw HTML
- Schema validation is disabled or bypassed for LLM responses

---

## 8. Rate Limiting & DoS Protection

```bash
# Check for rate limiting on expensive endpoints
grep -rn "brand_guide\|market_analysis\|competitive_analysis\|video_insight" $ARGUMENTS \
  | grep -v "rate_limit\|throttle\|token_budget"
```

**Flag if:**
- New expensive AI endpoints lack rate limiting
- No token budget check before expensive LLM calls

---

## Review Summary Template

After completing checks, summarize:

```
## Security Review Summary for: $ARGUMENTS

### Critical Issues (must fix before merge):
- [ ] None found OR
- [ ] Issue: [description] at [file:line]

### High Issues (should fix before merge):
- [ ] None found OR  
- [ ] Issue: [description] at [file:line]

### Medium Issues (track and fix soon):
- [ ] ...

### Low / Informational:
- [ ] ...

### HIPAA Compliance:
- PHI logging: ✅ Safe / ⚠️ Risk at [location]
- Audit logging: ✅ Present / ❌ Missing

### SOC2 Controls:
- Auth coverage: ✅ All routes protected / ⚠️ Missing on [routes]
- SQL injection: ✅ No issues / ❌ Found at [location]

### Recommendation:
[ ] APPROVE — no security concerns
[ ] APPROVE WITH COMMENTS — minor issues flagged
[ ] REQUEST CHANGES — critical issues must be resolved
```
