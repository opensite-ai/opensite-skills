# Example Finding

## [P1] Missing PHI scrubbing before error capture

**Why it matters**
The handler sends raw prompt text into `sentry::capture_message`, which violates the platform rule against logging user-submitted PHI or prompt content in production telemetry.

**What to verify**
- Confirm the prompt body can include patient or restaurant-specific identifiers.
- Confirm the same path is reachable in production.

**Recommended fix**
Hash or redact the prompt before capture, and attach only request ids or safe metadata to the event.
