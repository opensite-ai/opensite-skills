#!/usr/bin/env python3
"""
list_memories.py — List all memories with optional filtering and brief summaries.

Usage:
    python list_memories.py
    python list_memories.py --type semantic --brief
    python list_memories.py --project opensite-api
"""
import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MEMORY_ROOT = SCRIPT_DIR.parent / "store"


def parse_frontmatter(text):
    fm = {}
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
    return fm


def list_memories(memory_type=None, project=None, brief=False):
    if not MEMORY_ROOT.exists():
        print(f"⚠️  Memory store not found at {MEMORY_ROOT}")
        return

    entries = []
    for md_file in sorted(MEMORY_ROOT.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        if memory_type and memory_type != "all" and fm.get("type") != memory_type:
            continue
        if project and fm.get("project", "null") != project:
            continue
        entries.append((md_file, fm))

    by_type = defaultdict(list)
    for f, fm in entries:
        by_type[fm.get("type", "unknown")].append((f, fm))

    for mtype, items in sorted(by_type.items()):
        print(f"\n▸ {mtype.upper()} ({len(items)} entries)")
        print("─" * 60)
        for f, fm in items:
            rel = str(f.relative_to(MEMORY_ROOT.parent))
            title = fm.get("title", f.stem)
            created = fm.get("created", "?")
            conf = fm.get("confidence", "high")
            print(f"  {title}")
            if not brief:
                print(f"  Path:  {rel}")
                print(f"  Date:  {created}  |  Confidence: {conf}")
                print(f"  Tags:  {fm.get('tags', 'none')}")
                print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="List memory store entries")
    parser.add_argument("--type", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--brief", action="store_true")
    args = parser.parse_args()
    list_memories(memory_type=args.type, project=args.project, brief=args.brief)
