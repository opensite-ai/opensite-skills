# Testing OpenSite Skills

## How We Test AI Skills

AI skills present unique testing challenges because they often involve:

- Complex workflows that span multiple tools and contexts
- State management across long-running sessions
- Integration with external systems (databases, APIs, file systems)
- Non-deterministic behavior based on agent decisions

Our testing approach focuses on **practical verification** rather than traditional unit testing:

### 1. Smoke Testing
- **Purpose**: Verify that all scripts can run successfully with synthetic input
- **Scope**: End-to-end workflows using realistic but controlled data
- **Execution**: Bash-based test suites that validate expected outputs
- **Example**: `test_ctx.sh` for context-management skill

### 2. Regression Prevention
- **Purpose**: Catch unintended behavior changes between versions
- **Scope**: Core functionality that must remain stable
- **Execution**: Automated checks for specific output patterns
- **Example**: BM25 rank verification in context-management tests

### 3. Edge Case Coverage
- **Purpose**: Handle common failure modes gracefully
- **Scope**: Input validation, error conditions, resource limits
- **Execution**: Tests with malformed or extreme inputs
- **Example**: Unclosed code fence handling in chunk_content()

### 4. Cross-Platform Validation
- **Purpose**: Ensure compatibility across different environments
- **Scope**: Different SQLite versions, Python versions, OS platforms
- **Execution**: Conditional test logic that adapts to platform capabilities
- **Example**: FTS4/FTS5 fallback detection and graceful degradation

## Context-Management Skill Tests

The `context-management` skill includes a comprehensive 18-test smoke suite in `scripts/test_ctx.sh` that validates:

### Core Script Functionality
1. **ctx_index.py**: Indexing from stdin, files, and with tags
2. **ctx_search.py**: Basic queries, source filtering, stats display
3. **ctx_compress.py**: Compression with and without indexing
4. **ctx_checkpoint.py**: Save, load, JSON output, and listing
5. **ctx_stats.py**: Full and brief statistics reporting

### Advanced Features
6. **BM25 Ranking**: Verifies FTS5 ranking is active (or warns on FTS4)
7. **Source Management**: Delete specific sources and clear all content
8. **Auto-Injection**: Validates .gitignore auto-injection

### Edge Cases
- Unclosed code fences in markdown content
- Empty or minimal input handling
- Session isolation with CTX_SESSION_ID
- Rapid checkpoint saves (microsecond timestamp collision prevention)

### Test Design Principles

1. **Self-Contained**: Each test creates its own temporary project directory
2. **Cleanup Guaranteed**: `trap cleanup EXIT` ensures no test debris remains
3. **Clear Failure Messages**: Descriptive output on what failed and why
4. **Non-Blocking Warnings**: FTS4 fallback produces warnings, not failures
5. **Realistic Data**: Test content includes errors, warnings, code blocks, headings

### Running the Tests

```bash
# From the context-management directory
bash scripts/test_ctx.sh

# No chmod +x needed when using bash directly
# Works from any directory with full paths
bash /path/to/context-management/scripts/test_ctx.sh
```

### Test Output Interpretation

- ✅ **PASS**: Test completed successfully
- ⚠️ **WARN**: Expected limitation detected (e.g., FTS4 instead of FTS5)
- ❌ **FAIL**: Unexpected behavior or regression detected

### Future Test Enhancements

Planned improvements for the testing framework:
- **Performance Benchmarks**: Track compression ratios and search speeds
- **Concurrency Tests**: Validate multi-agent session isolation
- **Large Input Tests**: Handle files >100MB gracefully
- **Cross-Version Compatibility**: Test against multiple SQLite/Python versions

## Future Skill Test Sections

As we add testing to other skills, we'll document their approaches here:

### Memory System Tests
*(To be added when memory skill testing is implemented)*

### Research Agent Tests  
*(To be added when research skill testing is implemented)*

### Platform Sync Tests
*(To be added when platform sync skill testing is implemented)*

Each skill section will include:
- Test suite location and execution instructions
- Key scenarios covered
- Edge cases handled
- Platform-specific considerations
- Performance benchmarks (where applicable)
