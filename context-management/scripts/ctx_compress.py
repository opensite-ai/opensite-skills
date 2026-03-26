#!/usr/bin/env python3
"""
ctx_compress.py — Deterministic output compression for context window preservation.

Reduces large outputs to a fixed line budget using priority-based extraction:
  1. Error/warning lines (highest priority)
  2. Structure lines (headings, function signatures, test names)
  3. Content lines (everything else, sampled evenly)

Optionally indexes the full uncompressed content into the FTS5 database.

Usage:
    # Compress stdin to 50 lines (default)
    cat huge_log.txt | python ctx_compress.py

    # Compress to specific budget
    cargo test 2>&1 | python ctx_compress.py --lines 30

    # Compress AND index (recommended)
    cargo test 2>&1 | python ctx_compress.py --lines 40 \
      --index --source "test:cargo" --project /path

    # Compress a file
    python ctx_compress.py --file /tmp/output.txt --lines 60

No external dependencies. Python 3.8+.
"""

import argparse
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Patterns that indicate high-priority lines
ERROR_PATTERNS = [
    re.compile(r"\b(error|Error|ERROR|FAILED|FAIL|panic|PANIC)\b"),
    re.compile(r"\b(fatal|Fatal|FATAL|critical|CRITICAL)\b"),
    re.compile(r"\b(exception|Exception|EXCEPTION|traceback|Traceback)\b"),
    re.compile(r"^\s*\^+\s*$"),  # Caret error indicators
    re.compile(r"^E\s+\w"),  # pytest error lines
    re.compile(r"thread\s+'.*'\s+panicked"),  # Rust panics
]

WARNING_PATTERNS = [
    re.compile(r"\b(warning|Warning|WARNING|warn|WARN)\b"),
    re.compile(r"\b(deprecated|Deprecated|DEPRECATED)\b"),
    re.compile(r"^\s*⚠"),
]

STRUCTURE_PATTERNS = [
    re.compile(r"^#{1,6}\s"),  # Markdown headings
    re.compile(
        r"^(fn|def|class|function|interface|struct|enum|impl|mod|pub)\s"
    ),  # Declarations
    re.compile(r"^(test|it|describe|context|scenario)\s"),  # Test names
    re.compile(
        r"^(running|Compiling|Finished|Testing|Building)\s", re.IGNORECASE
    ),  # Build steps
    re.compile(r"^\s*(PASS|FAIL|ok|not ok)\s"),  # TAP/test results
    re.compile(r"^-{3,}|^={3,}|^\*{3,}"),  # Separators
    re.compile(r"^diff --git"),  # Git diff headers
    re.compile(r"^@@\s"),  # Diff hunks
    re.compile(r"^[+-]{3}\s[ab]/"),  # Diff file headers
]

# Lines to always skip (noise)
NOISE_PATTERNS = [
    re.compile(r"^\s*$"),  # Blank lines (we'll add our own spacing)
    re.compile(r"^\s*\.\s*$"),  # Progress dots
]


def classify_line(line: str) -> str:
    """Classify a line by priority: 'error', 'warning', 'structure', 'content', or 'noise'."""
    stripped = line.rstrip()

    for pat in NOISE_PATTERNS:
        if pat.search(stripped):
            return "noise"

    for pat in ERROR_PATTERNS:
        if pat.search(stripped):
            return "error"

    for pat in WARNING_PATTERNS:
        if pat.search(stripped):
            return "warning"

    for pat in STRUCTURE_PATTERNS:
        if pat.search(stripped):
            return "structure"

    return "content"


def compress(text: str, line_budget: int = 50) -> str:
    """
    Compress text to fit within line_budget lines using priority extraction.

    Priority order:
    1. Errors (always included, up to 40% of budget)
    2. Warnings (up to 15% of budget)
    3. Structure lines (up to 25% of budget)
    4. Content lines (fill remaining budget, evenly sampled)
    5. First 3 + last 3 lines (always included for orientation)
    """
    lines = text.splitlines()
    total_lines = len(lines)

    if total_lines <= line_budget:
        return text

    # Classify all lines
    classified = [(i, line, classify_line(line)) for i, line in enumerate(lines)]

    # Budget allocation
    error_budget = max(3, int(line_budget * 0.40))
    warning_budget = max(2, int(line_budget * 0.15))
    structure_budget = max(2, int(line_budget * 0.25))
    bookend_budget = 6  # 3 first + 3 last
    content_budget = max(2, line_budget - bookend_budget)

    selected = set()

    # Always include first 3 and last 3 non-noise lines
    non_noise = [(i, l, c) for i, l, c in classified if c != "noise"]
    for i, l, c in non_noise[:3]:
        selected.add(i)
    for i, l, c in non_noise[-3:]:
        selected.add(i)

    # Priority 1: Errors
    errors = [(i, l) for i, l, c in classified if c == "error"]
    for i, l in errors[:error_budget]:
        selected.add(i)
        # Include 1 line of context before and after errors
        if i > 0:
            selected.add(i - 1)
        if i < total_lines - 1:
            selected.add(i + 1)

    # Priority 2: Warnings
    if len(selected) < line_budget:
        warnings = [(i, l) for i, l, c in classified if c == "warning"]
        for i, l in warnings[:warning_budget]:
            selected.add(i)

    # Priority 3: Structure
    if len(selected) < line_budget:
        structures = [(i, l) for i, l, c in classified if c == "structure"]
        remaining = line_budget - len(selected)
        budget = min(remaining, structure_budget)
        # Evenly sample structure lines
        if len(structures) <= budget:
            for i, l in structures:
                selected.add(i)
        else:
            step = len(structures) / budget
            for j in range(budget):
                idx = int(j * step)
                selected.add(structures[idx][0])

    # Priority 4: Content (fill remaining)
    if len(selected) < line_budget:
        content = [
            (i, l) for i, l, c in classified if c == "content" and i not in selected
        ]
        remaining = line_budget - len(selected)
        if content and remaining > 0:
            step = max(1, len(content) // remaining)
            for j in range(0, len(content), step):
                if len(selected) >= line_budget:
                    break
                selected.add(content[j][0])

    # Build output in original order
    sorted_indices = sorted(selected)
    result_lines = []
    prev_idx = -1
    for idx in sorted_indices:
        if prev_idx >= 0 and idx - prev_idx > 1:
            omitted = idx - prev_idx - 1
            result_lines.append(f"  ... [{omitted} lines omitted] ...")
        result_lines.append(lines[idx])
        prev_idx = idx

    # Add trailing omission indicator if needed
    if sorted_indices and sorted_indices[-1] < total_lines - 1:
        omitted = total_lines - 1 - sorted_indices[-1]
        if omitted > 0:
            result_lines.append(f"  ... [{omitted} lines omitted] ...")

    return "\n".join(result_lines)


def read_input(args: argparse.Namespace) -> str:
    """Read content from the specified input source."""
    if args.file:
        return Path(args.file).read_text(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Error: no input. Use --file or pipe to stdin.", file=sys.stderr)
    sys.exit(1)


def log_compression(
    project_dir: str,
    source: str,
    original_lines: int,
    compressed_lines: int,
    original_bytes: int,
    compressed_bytes: int,
):
    """Log a compression event to the context DB for stats tracking."""
    ctx_dir = Path(project_dir).resolve() / ".ctx"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    db_path = ctx_dir / "context.db"

    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compression_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                original_lines INTEGER NOT NULL,
                compressed_lines INTEGER NOT NULL,
                original_bytes INTEGER NOT NULL,
                compressed_bytes INTEGER NOT NULL,
                savings_bytes INTEGER NOT NULL,
                ratio REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        savings = original_bytes - compressed_bytes
        ratio = compressed_bytes / original_bytes if original_bytes > 0 else 1.0
        conn.execute(
            """INSERT INTO compression_log
               (source, original_lines, compressed_lines, original_bytes,
                compressed_bytes, savings_bytes, ratio, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source,
                original_lines,
                compressed_lines,
                original_bytes,
                compressed_bytes,
                savings,
                ratio,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Stats logging should never break the main flow


def main():
    parser = argparse.ArgumentParser(
        description="Compress large outputs for context window preservation"
    )
    parser.add_argument(
        "--lines", type=int, default=50, help="Line budget (default: 50)"
    )
    parser.add_argument("--file", default=None, help="File to compress")
    parser.add_argument(
        "--index", action="store_true", help="Also index full content into FTS5 DB"
    )
    parser.add_argument(
        "--source", default=None, help="Source identifier (required with --index)"
    )
    parser.add_argument(
        "--project", default=".", help="Project directory (default: current dir)"
    )

    args = parser.parse_args()
    full_content = read_input(args)

    total_lines = len(full_content.splitlines())
    compressed = compress(full_content, args.lines)

    # Optionally index the full content
    if args.index:
        if not args.source:
            print("Error: --source is required when using --index.", file=sys.stderr)
            sys.exit(1)

        index_script = SCRIPT_DIR / "ctx_index.py"
        proc = subprocess.run(
            [
                sys.executable,
                str(index_script),
                "--source",
                args.source,
                "--project",
                args.project,
            ],
            input=full_content,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            print(f"Warning: indexing failed: {proc.stderr.strip()}", file=sys.stderr)
        index_note = f", full content indexed as '{args.source}'"
    else:
        index_note = ""

    # Output compressed result
    print(compressed)
    print(
        f"\n[compressed: {len(compressed.splitlines())}/{total_lines} lines{index_note}]"
    )

    # Log compression event for stats tracking
    source_label = args.source or "(stdin)"
    original_bytes = len(full_content.encode("utf-8"))
    compressed_bytes = len(compressed.encode("utf-8"))
    log_compression(
        args.project,
        source_label,
        total_lines,
        len(compressed.splitlines()),
        original_bytes,
        compressed_bytes,
    )


if __name__ == "__main__":
    main()
