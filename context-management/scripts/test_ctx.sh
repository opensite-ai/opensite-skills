#!/bin/bash
#
# test_ctx.sh — Smoke-test script for context-management skill
#
# Verifies that all scripts can run successfully against synthetic input.
# Run this after installation to catch broken setups before a long session.
#
# Usage:
#   cd /path/to/context-management
#   ./scripts/test_ctx.sh
#
# Exit codes:
#   0 — all tests passed
#   1 — one or more tests failed
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_PROJECT="/tmp/ctx-test-$$"

# Create test content with a heredoc to avoid shell interpretation
create_test_content() {
cat <<'EOF'
# Test File

This is a test file with multiple lines.
It has some error-like content: ERROR: something went wrong.
And some warning content: WARNING: deprecated API.
And some structure: ## Section Heading

```python
def test_function():
    return 42
```

End of test content.
EOF
}

TEST_CONTENT=$(create_test_content)

echo "=== Context Management Smoke Test ==="
echo ""

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up test directory..."
    rm -rf "$TEST_PROJECT"
}
trap cleanup EXIT

# Create test project directory
mkdir -p "$TEST_PROJECT"
cd "$TEST_PROJECT"

echo "Test project: $TEST_PROJECT"
echo ""

# Test 1: ctx_index.py from stdin
echo "Test 1: Indexing content from stdin..."
echo "$TEST_CONTENT" | python "$SCRIPT_DIR/ctx_index.py" \
    --source "test:stdin" \
    --project . \
    || { echo "  ✗ FAIL: ctx_index.py (stdin)"; exit 1; }
echo "  ✓ PASS: ctx_index.py (stdin)"

# Test 2: ctx_index.py from file
echo "$TEST_CONTENT" > test_file.txt
echo "Test 2: Indexing content from file..."
python "$SCRIPT_DIR/ctx_index.py" \
    --source "test:file" \
    --file test_file.txt \
    --project . \
    || { echo "  ✗ FAIL: ctx_index.py (file)"; exit 1; }
echo "  ✓ PASS: ctx_index.py (file)"

# Test 3: ctx_index.py with tags
echo "Test 3: Indexing content with tags..."
echo "$TEST_CONTENT" | python "$SCRIPT_DIR/ctx_index.py" \
    --source "test:tagged" \
    --tags "test,smoke,validation" \
    --project . \
    || { echo "  ✗ FAIL: ctx_index.py (with tags)"; exit 1; }
echo "  ✓ PASS: ctx_index.py (with tags)"

# Test 4: ctx_search.py basic query
echo "Test 4: Searching indexed content..."
RESULT=$(python "$SCRIPT_DIR/ctx_search.py" \
    --query "error" \
    --project .)
if echo "$RESULT" | grep -q "ERROR"; then
    echo "  ✓ PASS: ctx_search.py (basic query)"
else
    echo "  ✗ FAIL: ctx_search.py (basic query)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 5: ctx_search.py --list-sources
echo "Test 5: Listing indexed sources..."
RESULT=$(python "$SCRIPT_DIR/ctx_search.py" \
    --list-sources \
    --project .)
if echo "$RESULT" | grep -q "test:"; then
    echo "  ✓ PASS: ctx_search.py (list sources)"
else
    echo "  ✗ FAIL: ctx_search.py (list sources)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 6: ctx_search.py --stats
echo "Test 6: Showing database stats..."
RESULT=$(python "$SCRIPT_DIR/ctx_search.py" \
    --stats \
    --project .)
if echo "$RESULT" | grep -q "Total chunks"; then
    echo "  ✓ PASS: ctx_search.py (stats)"
else
    echo "  ✗ FAIL: ctx_search.py (stats)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 7: ctx_compress.py basic
echo "Test 7: Compressing content..."
RESULT=$(echo "$TEST_CONTENT" | python "$SCRIPT_DIR/ctx_compress.py" --lines 10)
if echo "$RESULT" | grep -q "compressed:"; then
    echo "  ✓ PASS: ctx_compress.py (basic)"
else
    echo "  ✗ FAIL: ctx_compress.py (basic)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 8: ctx_compress.py with --index
echo "Test 8: Compressing and indexing..."
RESULT=$(echo "$TEST_CONTENT" | python "$SCRIPT_DIR/ctx_compress.py" \
    --lines 10 \
    --index \
    --source "test:compressed" \
    --project .)
if echo "$RESULT" | grep -q "indexed as"; then
    echo "  ✓ PASS: ctx_compress.py (with --index)"
else
    echo "  ✗ FAIL: ctx_compress.py (with --index)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 9: ctx_checkpoint.py save
echo "Test 9: Saving checkpoint..."
python "$SCRIPT_DIR/ctx_checkpoint.py" save \
    --project . \
    --task "Test task with multiple clauses, including commas, in the description" \
    --completed "item1, item2, item3" \
    --in-progress "current work" \
    --next-steps "step1, step2" \
    --decisions "Decision A: use X, Decision B: avoid Y" \
    --context "Test context" \
    || { echo "  ✗ FAIL: ctx_checkpoint.py (save)"; exit 1; }
if [ -f .ctx/checkpoint.md ]; then
    echo "  ✓ PASS: ctx_checkpoint.py (save)"
else
    echo "  ✗ FAIL: ctx_checkpoint.py (save) - checkpoint file not created"
    exit 1
fi

# Test 10: ctx_checkpoint.py load
echo "Test 10: Loading checkpoint..."
RESULT=$(python "$SCRIPT_DIR/ctx_checkpoint.py" load --project .)
if echo "$RESULT" | grep -q "Test task"; then
    echo "  ✓ PASS: ctx_checkpoint.py (load)"
else
    echo "  ✗ FAIL: ctx_checkpoint.py (load)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 11: ctx_checkpoint.py load --json
echo "Test 11: Loading checkpoint as JSON..."
RESULT=$(python "$SCRIPT_DIR/ctx_checkpoint.py" load --project . --json)
if echo "$RESULT" | grep -q '"task"'; then
    echo "  ✓ PASS: ctx_checkpoint.py (load --json)"
else
    echo "  ✗ FAIL: ctx_checkpoint.py (load --json)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 12: ctx_checkpoint.py list
echo "Test 12: Listing checkpoints..."
RESULT=$(python "$SCRIPT_DIR/ctx_checkpoint.py" list --project .)
# Accept either archived checkpoints or no archived checkpoints
if echo "$RESULT" | grep -qE "(Archived|No archived)"; then
    echo "  ✓ PASS: ctx_checkpoint.py (list)"
else
    echo "  ✗ FAIL: ctx_checkpoint.py (list)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 13: ctx_stats.py
echo "Test 13: Showing compression stats..."
RESULT=$(python "$SCRIPT_DIR/ctx_stats.py" --project .)
if echo "$RESULT" | grep -q "Context Savings Report"; then
    echo "  ✓ PASS: ctx_stats.py"
else
    echo "  ✗ FAIL: ctx_stats.py"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 14: ctx_stats.py --brief
echo "Test 14: Brief stats output..."
RESULT=$(python "$SCRIPT_DIR/ctx_stats.py" --brief --project .)
if echo "$RESULT" | grep -q "ctx-stats:"; then
    echo "  ✓ PASS: ctx_stats.py (--brief)"
else
    echo "  ✗ FAIL: ctx_stats.py (--brief)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 15: ctx_search.py --delete-source
echo "Test 15: Deleting specific source..."
RESULT=$(python "$SCRIPT_DIR/ctx_search.py" \
    --delete-source "test:compressed" \
    --project .)
if echo "$RESULT" | grep -q "Deleted"; then
    echo "  ✓ PASS: ctx_search.py (--delete-source)"
else
    echo "  ✗ FAIL: ctx_search.py (--delete-source)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 16: ctx_search.py --clear-all
echo "Test 16: Clearing all content..."
RESULT=$(python "$SCRIPT_DIR/ctx_search.py" --clear-all --project .)
if echo "$RESULT" | grep -q "Cleared all"; then
    echo "  ✓ PASS: ctx_search.py (--clear-all)"
else
    echo "  ✗ FAIL: ctx_search.py (--clear-all)"
    echo "  Output: $RESULT"
    exit 1
fi

# Test 17: Verify .gitignore was auto-injected
echo "Test 17: Checking .gitignore auto-injection..."
if [ -f .gitignore ] && grep -q ".ctx/" .gitignore; then
    echo "  ✓ PASS: .gitignore auto-injection"
else
    echo "  ✗ FAIL: .gitignore auto-injection"; exit 1
fi

echo ""
echo "=== All Tests Passed ==="
echo ""
echo "Context management skill is ready for use."
exit 0
