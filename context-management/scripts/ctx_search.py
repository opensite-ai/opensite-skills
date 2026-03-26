#!/usr/bin/env python3
"""
ctx_search.py — Query the project-local SQLite FTS5 knowledge base.

Uses BM25 ranking for relevance-ordered retrieval of indexed content chunks.

Usage:
    # Basic keyword search
    python ctx_search.py --query "error handling" --project /path

    # Filter by source prefix
    python ctx_search.py --query "middleware" --source "file:src/" --project /path

    # Filter by tags
    python ctx_search.py --query "timeout" --tags "production" --project /path

    # List all indexed sources
    python ctx_search.py --list-sources --project /path

    # Show database stats
    python ctx_search.py --stats --project /path

    # Purge entries older than N days
    python ctx_search.py --purge-older-than 7 --project /path

No external dependencies. Python 3.8+.
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def get_db_path(project_dir: str) -> Path:
    """Resolve the .ctx/context.db path for the given project directory."""
    return Path(project_dir).resolve() / ".ctx" / "context.db"


def open_db(db_path: Path) -> sqlite3.Connection:
    """Open an existing context database. Exits if it doesn't exist."""
    if not db_path.exists():
        print(
            "No context database found. Index some content first with ctx_index.py.",
            file=sys.stderr,
        )
        sys.exit(1)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def search_fts(
    conn: sqlite3.Connection,
    query: str,
    source_prefix: str = None,
    tags_filter: str = None,
    limit: int = 10,
) -> list:
    """Search the FTS5 index with BM25 ranking."""
    # Build the FTS5 MATCH query
    # Strip all quotes from terms and filter out empty strings
    terms = [t.replace('"', '').replace("'", '') for t in query.split()]
    terms = [t for t in terms if t.strip()]

    if not terms:
        return []

    # Use individual terms with implicit AND
    fts_query = " ".join(f'"{t}"' for t in terms)

    try:
        # Try FTS5 bm25() function first
        sql = """
            SELECT
                c.id,
                c.source,
                c.chunk_index,
                c.content,
                c.tags,
                c.indexed_at,
                c.byte_size,
                bm25(chunks_fts, 1.0, 2.0, 0.5) AS rank
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.rowid
            WHERE chunks_fts MATCH ?
        """
        params = [fts_query]

        if source_prefix:
            sql += " AND c.source LIKE ?"
            params.append(f"{source_prefix}%")

        if tags_filter:
            for tag in tags_filter.split(","):
                tag = tag.strip()
                if tag:
                    sql += " AND c.tags LIKE ?"
                    params.append(f"%{tag}%")

        sql += " ORDER BY rank LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        # Fallback for FTS4 (no bm25 function)
        sql = """
            SELECT
                c.id,
                c.source,
                c.chunk_index,
                c.content,
                c.tags,
                c.indexed_at,
                c.byte_size,
                0 AS rank
            FROM chunks_fts f
            JOIN chunks c ON c.id = f.rowid
            WHERE chunks_fts MATCH ?
        """
        params = [fts_query]

        if source_prefix:
            sql += " AND c.source LIKE ?"
            params.append(f"{source_prefix}%")

        if tags_filter:
            for tag in tags_filter.split(","):
                tag = tag.strip()
                if tag:
                    sql += " AND c.tags LIKE ?"
                    params.append(f"%{tag}%")

        sql += " LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()

    return [dict(row) for row in rows]


def list_sources(conn: sqlite3.Connection) -> list:
    """List all distinct sources in the database."""
    rows = conn.execute("""
        SELECT source, COUNT(*) as chunk_count, SUM(byte_size) as total_bytes,
               MAX(indexed_at) as last_indexed
        FROM chunks
        GROUP BY source
        ORDER BY last_indexed DESC
    """).fetchall()
    return [dict(row) for row in rows]


def print_stats(conn: sqlite3.Connection):
    """Print database statistics."""
    total = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    sources = conn.execute("SELECT COUNT(DISTINCT source) FROM chunks").fetchone()[0]
    total_bytes = conn.execute(
        "SELECT COALESCE(SUM(byte_size), 0) FROM chunks"
    ).fetchone()[0]
    oldest = conn.execute("SELECT MIN(indexed_at) FROM chunks").fetchone()[0]
    newest = conn.execute("SELECT MAX(indexed_at) FROM chunks").fetchone()[0]

    print(f"\nContext DB Stats")
    print("-" * 40)
    print(f"  Total chunks:   {total:>8}")
    print(f"  Total sources:  {sources:>8}")
    print(f"  Total size:     {total_bytes:>8,} bytes")
    if oldest:
        print(f"  Oldest entry:   {oldest[:19]}")
    if newest:
        print(f"  Newest entry:   {newest[:19]}")
    print()


def purge_old(conn: sqlite3.Connection, days: int) -> int:
    """Delete entries older than N days. Returns count deleted."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    cursor = conn.execute("DELETE FROM chunks WHERE indexed_at < ?", (cutoff,))
    conn.commit()
    return cursor.rowcount


def delete_source(conn: sqlite3.Connection, source: str, exact: bool = True) -> int:
    """Delete entries for a specific source. Returns count deleted."""
    if exact:
        cursor = conn.execute("DELETE FROM chunks WHERE source = ?", (source,))
    else:
        cursor = conn.execute("DELETE FROM chunks WHERE source LIKE ?", (f"{source}%",))
    conn.commit()
    return cursor.rowcount


def clear_all(conn: sqlite3.Connection) -> int:
    """Delete all indexed content. Returns count deleted."""
    cursor = conn.execute("DELETE FROM chunks")
    conn.commit()
    return cursor.rowcount


def format_snippet(content: str, max_lines: int = 15) -> str:
    """Trim a content chunk for display."""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return content.rstrip()
    half = max_lines // 2
    head = lines[:half]
    tail = lines[-half:]
    omitted = len(lines) - max_lines
    return (
        "\n".join(head) + f"\n  ... [{omitted} lines omitted] ...\n" + "\n".join(tail)
    )


def main():
    parser = argparse.ArgumentParser(
        description="Search the context FTS5 knowledge base"
    )
    parser.add_argument("--query", default=None, help="Search query (BM25 ranked)")
    parser.add_argument(
        "--source", default=None, help="Filter by source prefix (e.g., 'file:src/')"
    )
    parser.add_argument("--tags", default=None, help="Filter by tags (comma-separated)")
    parser.add_argument(
        "--limit", type=int, default=10, help="Max results (default: 10)"
    )
    parser.add_argument(
        "--project", default=".", help="Project directory (default: current dir)"
    )
    parser.add_argument(
        "--full", action="store_true", help="Show full chunk content (no truncation)"
    )
    parser.add_argument(
        "--list-sources", action="store_true", help="List all indexed sources"
    )
    parser.add_argument("--stats", action="store_true", help="Show database statistics")
    parser.add_argument(
        "--purge-older-than",
        type=int,
        default=None,
        help="Delete entries older than N days",
    )
    parser.add_argument(
        "--delete-source",
        default=None,
        help="Delete entries for a specific source (use --prefix for prefix match)",
    )
    parser.add_argument(
        "--prefix",
        action="store_true",
        help="Use prefix matching with --delete-source",
    )
    parser.add_argument(
        "--clear-all",
        action="store_true",
        help="Delete all indexed content (clear the entire database)",
    )

    args = parser.parse_args()
    db_path = get_db_path(args.project)
    conn = open_db(db_path)

    try:
        if args.stats:
            print_stats(conn)
            return

        if args.list_sources:
            sources = list_sources(conn)
            if not sources:
                print("  No sources indexed yet.")
                return
            print(f"\nIndexed Sources ({len(sources)} total)")
            print("-" * 60)
            for s in sources:
                print(
                    f"  {s['source']:<40} {s['chunk_count']:>3} chunks  {s['total_bytes']:>8,}B"
                )
            print()
            return

        if args.purge_older_than is not None:
            deleted = purge_old(conn, args.purge_older_than)
            print(f"Purged {deleted} chunks older than {args.purge_older_than} days.")
            return

        if args.delete_source is not None:
            exact = not args.prefix
            deleted = delete_source(conn, args.delete_source, exact=exact)
            match_type = "exact match" if exact else "prefix match"
            print(f"Deleted {deleted} chunks for source '{args.delete_source}' ({match_type}).")
            return

        if args.clear_all:
            deleted = clear_all(conn)
            print(f"Cleared all indexed content: {deleted} chunks deleted.")
            return

        if not args.query:
            print(
                "Error: --query is required for search. Use --stats or --list-sources for info.",
                file=sys.stderr,
            )
            sys.exit(1)

        results = search_fts(
            conn,
            query=args.query,
            source_prefix=args.source,
            tags_filter=args.tags,
            limit=args.limit,
        )

        if not results:
            print(f"  No results for: {args.query}")
            return

        for r in results:
            rank_str = f"{r['rank']:.4f}" if r["rank"] != 0 else "n/a"
            print(f"\n[{rank_str}] {r['source']} (chunk {r['chunk_index']})")
            if r["tags"]:
                print(f"  tags: {r['tags']}")

            content = r["content"] if args.full else format_snippet(r["content"])
            for line in content.splitlines():
                print(f"  {line}")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
