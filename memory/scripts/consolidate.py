#!/usr/bin/env python3
"""
consolidate.py — Memory maintenance: decay confidence, detect duplicates,
compress old sessions, rebuild index.

Usage:
    python consolidate.py                   # full maintenance run
    python consolidate.py --dry-run         # preview without writing
    python consolidate.py --decay-only      # only apply confidence decay
"""
import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MEMORY_ROOT = SCRIPT_DIR.parent / "store"

DECAY_RULES = [
    ("high",   90, "medium"),
    ("medium", 60, "low"),
    ("low",    30, "archived"),
]


def parse_frontmatter(text):
    fm = {}
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
    return fm


def update_frontmatter_field(text, field, new_value):
    pattern = rf"^{field}: .*$"
    return re.sub(pattern, f"{field}: {new_value}", text, flags=re.MULTILINE)


def apply_confidence_decay(dry_run=False):
    changed = 0
    archived = 0
    now = datetime.now()

    for md_file in MEMORY_ROOT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        fm = parse_frontmatter(text)

        # Skip working memory and episodic sessions
        if fm.get("type") in ("working", "episodic"):
            continue

        current_conf = fm.get("confidence", "high")
        created_str = fm.get("created", str(now.date()))
        try:
            created = datetime.strptime(created_str, "%Y-%m-%d")
        except ValueError:
            continue
        age_days = (now - created).days

        for from_conf, threshold_days, to_conf in DECAY_RULES:
            if current_conf == from_conf and age_days >= threshold_days:
                if to_conf == "archived":
                    if not dry_run:
                        new_text = update_frontmatter_field(text, "confidence", "archived")
                        md_file.write_text(new_text, encoding="utf-8")
                    print(f"  📦 Archived (age {age_days}d): {md_file.name}")
                    archived += 1
                else:
                    if not dry_run:
                        new_text = update_frontmatter_field(text, "confidence", to_conf)
                        md_file.write_text(new_text, encoding="utf-8")
                    print(f"  ⬇️  Decayed {from_conf}→{to_conf} (age {age_days}d): {md_file.name}")
                    changed += 1
                break

    return changed, archived


def find_duplicate_titles():
    title_map = defaultdict(list)
    for md_file in MEMORY_ROOT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            fm = parse_frontmatter(text)
            title = fm.get("title", "").strip().lower()
            if title:
                title_map[title].append(md_file)
        except Exception:
            continue
    return {t: files for t, files in title_map.items() if len(files) > 1}


def compress_old_sessions(dry_run=False, threshold_days=90):
    sessions_dir = MEMORY_ROOT / "episodic" / "sessions"
    if not sessions_dir.exists():
        return 0

    archive_dir = sessions_dir / "archive"
    cutoff = datetime.now() - timedelta(days=threshold_days)
    compressed = 0

    old_sessions = []
    for md_file in sorted(sessions_dir.glob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            fm = parse_frontmatter(text)
            created_str = fm.get("created", "")
            created = datetime.strptime(created_str, "%Y-%m-%d")
            if created < cutoff:
                old_sessions.append((created, md_file, text, fm))
        except Exception:
            continue

    # Group by month
    by_month = defaultdict(list)
    for created, f, text, fm in old_sessions:
        month_key = created.strftime("%Y-%m")
        by_month[month_key].append((created, f, text, fm))

    for month_key, sessions in by_month.items():
        if len(sessions) < 2:
            continue

        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
            summary_path = sessions_dir / f"{month_key}-monthly-summary.md"
            combined = f"---\nid: monthly-{month_key}\ntype: episodic\ncategory: sessions\ntitle: Monthly Summary {month_key}\ntags: [monthly-summary, archived]\nproject: null\ncreated: {month_key}-01\nupdated: {datetime.now().strftime('%Y-%m-%d')}\nconfidence: high\n---\n\n# Monthly Summary: {month_key}\n\n"
            for _, f, text, fm in sorted(sessions):
                title = fm.get("title", f.stem)
                combined += f"## {title}\n\n"
                body_match = re.search(r"---\n.*?---\n(.*)", text, re.DOTALL)
                if body_match:
                    combined += body_match.group(1).strip()[:500] + "\n\n"
            summary_path.write_text(combined, encoding="utf-8")

            for _, f, _, _ in sessions:
                f.rename(archive_dir / f.name)

        print(f"  📁 Compressed {len(sessions)} sessions from {month_key} into monthly summary")
        compressed += len(sessions)

    return compressed


def run_maintenance(dry_run=False, decay_only=False):
    print("\n🧠 OpenSite Memory Consolidation")
    print("─" * 50)
    if dry_run:
        print("  DRY RUN — no files will be written\n")

    # Step 1: Confidence decay
    print("\n📉 Applying confidence decay...")
    changed, archived = apply_confidence_decay(dry_run=dry_run)
    print(f"  Decayed: {changed}  |  Archived: {archived}")

    if not decay_only:
        # Step 2: Duplicates
        print("\n🔍 Scanning for duplicate titles...")
        dupes = find_duplicate_titles()
        if dupes:
            for title, files in dupes.items():
                print(f"  ⚠️  Duplicate: \"{title}\"")
                for f in files:
                    print(f"     → {f.relative_to(MEMORY_ROOT.parent)}")
        else:
            print("  ✅ No duplicates found")

        # Step 3: Compress old sessions
        print("\n📦 Compressing old episodic sessions (>90 days)...")
        compressed = compress_old_sessions(dry_run=dry_run)
        if compressed == 0:
            print("  ✅ No sessions eligible for compression")

        # Step 4: Rebuild index
        if not dry_run:
            print("\n🗂️  Rebuilding search index...")
            sys.path.insert(0, str(SCRIPT_DIR))
            from search_memory import build_index
            build_index()

    print("\n══════════════════════════════════════════════════")
    print("  ✅ Consolidation complete")
    print("══════════════════════════════════════════════════\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run memory consolidation maintenance")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    parser.add_argument("--decay-only", action="store_true", help="Only apply confidence decay")
    args = parser.parse_args()
    run_maintenance(dry_run=args.dry_run, decay_only=args.decay_only)
