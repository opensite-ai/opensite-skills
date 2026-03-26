#!/usr/bin/env python3
"""
ctx_index.py — Index content into a project-local SQLite FTS5 database.

Chunks content by markdown headings (preserving code blocks intact), then inserts
each chunk into an FTS5 virtual table for BM25-ranked retrieval.

Usage:
    # Index from stdin
    cat large_file.rs | python ctx_index.py --source "file:src/main.rs" --project /path

    # Index from a file
    python ctx_index.py --source "git:diff" --file /tmp/diff.txt --project /path

    # Index inline content
    python ctx_index.py --source "test:cargo" --content "test output here" --project /path

    # With tags for filtered search
    python ctx_index.py --source "log:deploy" --tags "deploy,prod" --project . < deploy.log

No external dependencies. Python 3.8+.
"""

import argparse
import hashlib
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def get_session_id() -> str:
    """Get the current session ID from environment variable (for isolation)."""
    return os.environ.get("CTX_SESSION_ID", "")


def qualify_source(source: str, session_id: str = None) -> str:
    """Qualify a source identifier with session ID if present."""
    sid = session_id if session_id is not None else get_session_id()
    if sid:
        return f"{sid}:{source}"
    return source


def get_db_path(project_dir: str) -> Path:
    """Resolve the .ctx/context.db path for the given project directory."""
    ctx_dir = Path(project_dir).resolve() / ".ctx"
    ctx_dir.mkdir(parents=True, exist_ok=True)
    return ctx_dir / "context.db"


def ensure_gitignore(project_dir: str) -> None:
    """Ensure .ctx/ is in the project's .gitignore (first-run safety)."""
    project_path = Path(project_dir).resolve()
    gitignore_path = project_path / ".gitignore"

    # Check if .ctx/ is already in .gitignore
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8", errors="replace")
        if ".ctx/" in content or ".ctx" in content:
            return  # Already present

    # Append .ctx/ entry to .gitignore
    entry = "\n# Context management data (session-local, not committed)\n.ctx/\n"
    try:
        with gitignore_path.open("a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass  # Silently fail if we can't write .gitignore (permissions, etc.)


def init_db(db_path: Path, project_dir: str = None) -> sqlite3.Connection:
    """Create the FTS5 table if it doesn't exist."""
    # Auto-inject .gitignore on first run
    if project_dir:
        ensure_gitignore(project_dir)

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")

    # Main chunks table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            tags TEXT DEFAULT '',
            indexed_at TEXT NOT NULL,
            byte_size INTEGER NOT NULL
        )
    """)

    # Detect FTS5 availability
    has_fts5 = sqlite3.sqlite_version_info >= (3, 9, 0)

    # Create appropriate FTS virtual table
    if has_fts5:
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                source,
                content,
                tags,
                content='chunks',
                content_rowid='id',
                tokenize='porter unicode61'
            )
        """)
        # FTS5 triggers use special delete syntax
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, source, content, tags)
                VALUES (new.id, new.source, new.content, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, source, content, tags)
                VALUES ('delete', old.id, old.source, old.content, old.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                INSERT INTO chunks_fts(chunks_fts, rowid, source, content, tags)
                VALUES ('delete', old.id, old.source, old.content, old.tags);
                INSERT INTO chunks_fts(rowid, source, content, tags)
                VALUES (new.id, new.source, new.content, new.tags);
            END;
        """)
    else:
        # FTS4 fallback (no BM25 ranking available)
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts4(
                source,
                content,
                tags,
                content='chunks',
                tokenize=porter
            )
        """)
        # FTS4 triggers use standard DELETE syntax
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, source, content, tags)
                VALUES (new.id, new.source, new.content, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.id;
            END;

            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.id;
                INSERT INTO chunks_fts(rowid, source, content, tags)
                VALUES (new.id, new.source, new.content, new.tags);
            END;
        """)

    conn.commit()
    return conn


def chunk_content(text: str, max_chunk_lines: int = 80) -> list:
    """
    Split content into chunks by markdown headings, preserving code blocks intact.

    Strategy:
    1. Split on ## headings (keeping the heading with its section)
    2. If a section exceeds max_chunk_lines, split on blank lines
    3. Never split inside a code fence (``` ... ```)
    """
    if not text.strip():
        return []

    lines = text.splitlines(keepends=True)

    # First pass: identify code fence regions
    in_fence = False
    fence_regions = set()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
        if in_fence:
            fence_regions.add(i)

    # Auto-close unclosed fence at EOF
    if in_fence:
        fence_regions.discard(len(lines) - 1)  # treat as closed at EOF

    # Second pass: split on headings (not inside fences)
    sections = []
    current = []
    for i, line in enumerate(lines):
        if i not in fence_regions and re.match(r"^#{1,4}\s", line) and current:
            sections.append("".join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("".join(current))

    # Third pass: split oversized sections on blank lines
    chunks = []
    for section in sections:
        sec_lines = section.splitlines(keepends=True)
        if len(sec_lines) <= max_chunk_lines:
            chunks.append(section)
            continue

        # Split on double newlines, respecting fence regions
        sub_chunk = []
        sub_len = 0
        in_fence_local = False
        for line in sec_lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                in_fence_local = not in_fence_local

            sub_chunk.append(line)
            sub_len += 1

            if (
                not in_fence_local
                and stripped == ""
                and sub_len >= max_chunk_lines // 2
            ):
                chunks.append("".join(sub_chunk))
                sub_chunk = []
                sub_len = 0

        if sub_chunk:
            chunks.append("".join(sub_chunk))

    return [c for c in chunks if c.strip()]


def index_content(
    conn: sqlite3.Connection,
    source: str,
    content: str,
    tags: str = "",
    session_id: str = None,
) -> dict:
    """Index content into the FTS5 database. Returns stats."""
    now = datetime.now().isoformat()

    # Qualify source with session ID if present
    qualified_source = qualify_source(source, session_id=session_id)

    # Remove old entries for this source (re-index)
    conn.execute("DELETE FROM chunks WHERE source = ?", (qualified_source,))

    chunks = chunk_content(content)
    if not chunks:
        # Index the whole thing as one chunk if chunking produced nothing
        chunks = [content]

    total_bytes = 0
    for i, chunk in enumerate(chunks):
        content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()[:16]
        byte_size = len(chunk.encode("utf-8"))
        total_bytes += byte_size

        conn.execute(
            """INSERT INTO chunks (source, chunk_index, content, content_hash,
               tags, indexed_at, byte_size)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (qualified_source, i, chunk, content_hash, tags, now, byte_size),
        )

    conn.commit()
    return {
        "source": qualified_source,
        "chunks": len(chunks),
        "total_bytes": total_bytes,
        "indexed_at": now,
    }


def read_input(args: argparse.Namespace) -> str:
    """Read content from the specified input source."""
    if args.content is not None:
        return args.content
    if args.file:
        return Path(args.file).read_text(encoding="utf-8", errors="replace")
    # Default: read from stdin
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print(
        "Error: no input provided. Use --content, --file, or pipe to stdin.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Index content into the context FTS5 database"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Source identifier (e.g., 'file:src/main.rs', 'test:cargo')",
    )
    parser.add_argument(
        "--project", default=".", help="Project directory (default: current dir)"
    )
    parser.add_argument("--tags", default="", help="Comma-separated tags for filtering")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--content", help="Inline content to index")
    input_group.add_argument("--file", help="File path to read and index")

    args = parser.parse_args()
    content = read_input(args)

    db_path = get_db_path(args.project)
    conn = init_db(db_path, project_dir=args.project)

    try:
        stats = index_content(
            conn, args.source, content, args.tags, session_id=get_session_id()
        )
        print(
            f"Indexed {stats['source']}: "
            f"{stats['chunks']} chunks, "
            f"{stats['total_bytes']:,} bytes"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
