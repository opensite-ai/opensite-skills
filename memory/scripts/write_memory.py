#!/usr/bin/env python3
"""
write_memory.py — Atomic memory writer with frontmatter, deduplication guard,
and JSON index management.

Usage:
    python write_memory.py --type episodic --category sessions \
        --title "Session: 2026-03-25 rust-axum" \
        --content "Worked on..." --tags "rust,axum,session" --project opensite-api

No external dependencies required. Python 3.8+ only.
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MEMORY_ROOT = SCRIPT_DIR.parent / "store"
META_DIR = SCRIPT_DIR.parent / "meta"
INDEX_FILE = META_DIR / "index.json"

VALID_TYPES = {"episodic", "semantic", "procedural", "working"}
VALID_CATEGORIES = {
    "episodic": ["sessions", "events"],
    "semantic": ["projects", "people", "technologies", "domain"],
    "procedural": ["workflows", "decisions", "conventions"],
    "working": ["active"],
}


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:64]


def load_index() -> dict:
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"entries": {}, "tags": {}, "last_updated": None}


def save_index(index: dict):
    META_DIR.mkdir(parents=True, exist_ok=True)
    index["last_updated"] = datetime.now().isoformat()
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")


def yaml_quote(value: str) -> str:
    """
    Return value wrapped in double quotes if it contains a YAML-unsafe sequence
    (colon-space, leading/trailing whitespace, or special leading characters).
    Internal double quotes are escaped.
    """
    needs_quoting = (
        ": " in value
        or value != value.strip()
        or value[:1] in ('"', "'", "{", "[", ">", "|", "!", "%", "@", "`")
    )
    if needs_quoting:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def make_frontmatter(
    entry_id: str,
    memory_type: str,
    category: str,
    title: str,
    tags: list,
    project: str,
    confidence: str,
    date_str: str,
) -> str:
    tag_list = ", ".join(tags) if tags else ""
    return (
        f"---\n"
        f"id: {entry_id}\n"
        f"type: {memory_type}\n"
        f"category: {category}\n"
        f"title: {yaml_quote(title)}\n"
        f"tags: [{tag_list}]\n"
        f"project: {project or 'null'}\n"
        f"created: {date_str}\n"
        f"updated: {date_str}\n"
        f"confidence: {confidence}\n"
        f"---\n"
    )


def extract_summary(content: str) -> str:
    lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
    return " ".join(lines[:3])[:200]


def write_memory(
    memory_type: str,
    category: str,
    title: str,
    content: str,
    tags: list,
    project: str = None,
    confidence: str = "high",
    overwrite: bool = False,
) -> Path:
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = slugify(title)

    if memory_type == "working":
        category = "active"
        overwrite = True
        target_dir = MEMORY_ROOT / memory_type
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / "active.md"
        entry_id = "working-active"
    elif memory_type == "episodic" and category == "sessions":
        filename = f"{date_str}-{slug}.md"
        target_dir = MEMORY_ROOT / memory_type / category
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        entry_id = str(uuid.uuid4())[:8]
    else:
        filename = f"{slug}.md"
        target_dir = MEMORY_ROOT / memory_type / category
        if memory_type == "semantic" and category == "projects" and project:
            target_dir = target_dir / slugify(project)
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        entry_id = str(uuid.uuid4())[:8]

    if target_path.exists() and not overwrite:
        # Append update block to existing file
        existing = target_path.read_text(encoding="utf-8")
        updated_content = re.sub(
            r"^updated: .*$", f"updated: {date_str}", existing, flags=re.MULTILINE
        )
        updated_content += f"\n\n## Update: {date_str}\n\n{content.strip()}\n"
        target_path.write_text(updated_content, encoding="utf-8")
        print(
            f"✏️  Updated existing: {target_path.relative_to(MEMORY_ROOT.parent.parent)}"
        )
    else:
        if memory_type == "working":
            full_content = (
                make_frontmatter(
                    entry_id,
                    memory_type,
                    category,
                    title,
                    tags,
                    project,
                    confidence,
                    date_str,
                )
                + f"\n# {title}\n\n"
                + f"{content.strip()}\n"
            )
        else:
            summary = extract_summary(content)
            full_content = (
                make_frontmatter(
                    entry_id,
                    memory_type,
                    category,
                    title,
                    tags,
                    project,
                    confidence,
                    date_str,
                )
                + f"\n# {title}\n\n"
                + f"## Summary\n{summary}\n\n"
                + f"## Content\n{content.strip()}\n"
            )
        target_path.write_text(full_content, encoding="utf-8")
        print(f"✅ Written: {target_path.relative_to(MEMORY_ROOT.parent.parent)}")

    # Update index
    index = load_index()
    index["entries"][entry_id] = {
        "path": str(target_path.relative_to(MEMORY_ROOT.parent)),
        "title": title,
        "type": memory_type,
        "category": category,
        "project": project,
        "tags": tags,
        "created": date_str,
        "summary": extract_summary(content),
    }
    for tag in tags:
        index["tags"].setdefault(tag, []).append(entry_id)
    save_index(index)

    return target_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Write a memory entry to the OpenSite memory store"
    )
    parser.add_argument("--type", required=True, choices=list(VALID_TYPES))
    parser.add_argument("--category", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--content", required=True)
    parser.add_argument("--tags", default="", help="Comma-separated list of tags")
    parser.add_argument("--project", default=None)
    parser.add_argument(
        "--confidence", default="high", choices=["high", "medium", "low"]
    )
    parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args()
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    write_memory(
        memory_type=args.type,
        category=args.category,
        title=args.title,
        content=args.content,
        tags=tags,
        project=args.project,
        confidence=args.confidence,
        overwrite=args.overwrite,
    )
