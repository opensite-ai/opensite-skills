# Activation Guide

## Best-Fit Tasks
- Security-focused code review for OpenSite/Toastability platform.
- Best trigger phrase: reviewing PRs for security issues, auditing new API endpoints, checking for HIPAA/SOC2 compliance violations, reviewing Rust unsafe code, or scanning for injection vulnerabilities, data leakage, or auth bypasses. Auto-activates when reviewing code changes involving auth, LLM calls, user data, or external API integrations.

## Explicit Invocation
- `Use $code-review-security when reviewing PRs for security issues, auditing new API endpoints, checking for HIPAA/SOC2 compliance violations, reviewing Rust unsafe code, or scanning for injection vulnerabilities, data leakage, or auth bypasses. Auto-activates when reviewing code changes involving auth, LLM calls, user data, or external API integrations.`

## Cross-Agent Notes
- Start with `SKILL.md`, then load only the linked files you need.
- The standard metadata and this guide are portable across skills-compatible agents; Claude-specific frontmatter is optional and should degrade cleanly elsewhere.
