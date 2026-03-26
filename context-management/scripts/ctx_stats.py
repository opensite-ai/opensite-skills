#!/usr/bin/env python3
"""
ctx_stats.py — Context savings dashboard for the context-management skill.

Reads the compression_log table from the project's .ctx/context.db and shows
cumulative stats on how much context window budget has been saved.

Usage:
    # Full stats dashboard
    python ctx_stats.py --project /path/to/project

    # Brief one-liner (good for quick checks)
    python ctx_stats.py --brief --project .

    # Stats for current session only (last 4 hours)
    python ctx_stats.py --session --project .

    # Reset the compression log
    python ctx_stats.py --reset --project .

No external dependencies. Python 3.8+.
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

# Approximate tokens-per-byte ratio for mixed code/text content.
# GPT-4/Claude tokenizers average ~3.5-4 chars per token for code.
CHARS_PER_TOKEN = 3.8


def get_db_path(project_dir: str) -> Path:
    return Path(project_dir).resolve() / ".ctx" / "context.db"


def open_db(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        print(
            "No context database found. Run ctx_compress.py first to start tracking.",
            file=sys.stderr,
        )
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table(conn: sqlite3.Connection) -> bool:
    """Check if the compression_log table exists."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='compression_log'"
    ).fetchone()
    return row is not None


def bytes_to_tokens(byte_count: int) -> int:
    """Estimate token count from byte count."""
    return int(byte_count / CHARS_PER_TOKEN)


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    if b < 1024 * 1024:
        return f"{b / 1024:.1f} KB"
    return f"{b / (1024 * 1024):.1f} MB"


def print_full_stats(conn: sqlite3.Connection, since: str = None):
    """Print the full stats dashboard."""
    where = ""
    params = []
    if since:
        where = "WHERE timestamp >= ?"
        params = [since]

    row = conn.execute(
        f"""
        SELECT
            COUNT(*) as compressions,
            COALESCE(SUM(original_bytes), 0) as total_original,
            COALESCE(SUM(compressed_bytes), 0) as total_compressed,
            COALESCE(SUM(savings_bytes), 0) as total_savings,
            COALESCE(AVG(ratio), 1.0) as avg_ratio,
            COALESCE(SUM(original_lines), 0) as total_orig_lines,
            COALESCE(SUM(compressed_lines), 0) as total_comp_lines,
            MIN(timestamp) as first_event,
            MAX(timestamp) as last_event
        FROM compression_log {where}
    """,
        params,
    ).fetchone()

    compressions = row["compressions"]
    if compressions == 0:
        print("  No compression events recorded yet.")
        return

    total_original = row["total_original"]
    total_compressed = row["total_compressed"]
    total_savings = row["total_savings"]
    avg_ratio = row["avg_ratio"]
    total_orig_lines = row["total_orig_lines"]
    total_comp_lines = row["total_comp_lines"]
    first = row["first_event"][:19] if row["first_event"] else "n/a"
    last = row["last_event"][:19] if row["last_event"] else "n/a"

    saved_tokens = bytes_to_tokens(total_savings)
    original_tokens = bytes_to_tokens(total_original)
    pct_saved = (total_savings / total_original * 100) if total_original > 0 else 0

    scope = "Session" if since else "All-Time"
    print(f"\nContext Savings Report ({scope})")
    print("=" * 50)
    print(f"  Compressions:       {compressions:>8}")
    print(
        f"  Original size:      {format_bytes(total_original):>8}  (~{original_tokens:,} tokens)"
    )
    print(f"  Compressed size:    {format_bytes(total_compressed):>8}")
    print(
        f"  Total saved:        {format_bytes(total_savings):>8}  (~{saved_tokens:,} tokens)"
    )
    print(f"  Context saved:      {pct_saved:>7.1f}%")
    print(f"  Avg compression:    {avg_ratio:>7.1%}")
    print(
        f"  Lines: {total_orig_lines:,} -> {total_comp_lines:,} ({total_orig_lines - total_comp_lines:,} eliminated)"
    )
    print(f"  Period: {first} to {last}")
    print()

    # Per-source breakdown (top 10)
    rows = conn.execute(
        f"""
        SELECT
            source,
            COUNT(*) as count,
            SUM(savings_bytes) as saved,
            AVG(ratio) as avg_ratio
        FROM compression_log {where}
        GROUP BY source
        ORDER BY saved DESC
        LIMIT 10
    """,
        params,
    ).fetchall()

    if rows:
        print("Top Sources by Savings")
        print("-" * 50)
        for r in rows:
            print(
                f"  {r['source']:<30} {r['count']:>3}x  saved {format_bytes(r['saved']):>8}  ({r['avg_ratio']:.0%} ratio)"
            )
        print()


def print_brief(conn: sqlite3.Connection):
    """Print a one-line summary."""
    row = conn.execute("""
        SELECT
            COUNT(*) as n,
            COALESCE(SUM(savings_bytes), 0) as saved,
            COALESCE(SUM(original_bytes), 0) as orig
        FROM compression_log
    """).fetchone()

    if row["n"] == 0:
        print("ctx-stats: no compressions yet")
        return

    pct = (row["saved"] / row["orig"] * 100) if row["orig"] > 0 else 0
    tokens_saved = bytes_to_tokens(row["saved"])
    print(
        f"ctx-stats: {row['n']} compressions, ~{tokens_saved:,} tokens saved ({pct:.0f}% reduction)"
    )


def reset_log(conn: sqlite3.Connection):
    """Clear the compression log."""
    conn.execute("DELETE FROM compression_log")
    conn.commit()
    print("Compression log cleared.")


def main():
    parser = argparse.ArgumentParser(description="Context savings dashboard")
    parser.add_argument("--project", default=".", help="Project directory")
    parser.add_argument("--brief", action="store_true", help="One-line summary")
    parser.add_argument(
        "--session",
        action="store_true",
        help="Current session only (configurable via --session-hours)",
    )
    parser.add_argument(
        "--session-hours",
        type=int,
        default=4,
        help="Session window in hours (default: 4)",
    )
    parser.add_argument(
        "--reset", action="store_true", help="Clear the compression log"
    )

    args = parser.parse_args()

    # Warn if --session-hours is used without --session
    if args.session_hours != 4 and not args.session:
        print(
            "Warning: --session-hours has no effect without --session.", file=sys.stderr
        )

    db_path = get_db_path(args.project)
    conn = open_db(db_path)

    if not ensure_table(conn):
        print("  No compression events recorded yet. Use ctx_compress.py first.")
        conn.close()
        return

    try:
        if args.reset:
            reset_log(conn)
        elif args.brief:
            print_brief(conn)
        elif args.session:
            since = (datetime.now() - timedelta(hours=args.session_hours)).isoformat()
            print_full_stats(conn, since=since)
        else:
            print_full_stats(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
