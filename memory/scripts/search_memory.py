#!/usr/bin/env python3
"""
search_memory.py — Keyword + TF-IDF memory search over the OpenSite memory store.

Usage:
    python search_memory.py --query "rust axum"
    python search_memory.py --query "deploy" --type procedural --category workflows
    python search_memory.py --type episodic --sort recency --limit 5
    python search_memory.py --rebuild-index
    python search_memory.py --stats

No external dependencies. Python 3.8+.
"""
import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MEMORY_ROOT = SCRIPT_DIR.parent / "store"
INDEX_FILE = SCRIPT_DIR.parent / "meta" / "index.json"


def parse_frontmatter(text: str) -> dict:
    fm = {}
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ": " in line:
                k, _, v = line.partition(": ")
                fm[k.strip()] = v.strip()
    return fm


def extract_summary(text: str, fm: dict) -> str:
    m = re.search(r"## Summary\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
    if m:
        return m.group(1).strip()[:200]
    lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("#") and not l.startswith("---")]
    return " ".join(lines[:2])[:200]


def keyword_score(query: str, text: str) -> float:
    terms = query.lower().split()
    if not terms:
        return 1.0
    text_lower = text.lower()
    hits = sum(1 for t in terms if t in text_lower)
    return hits / len(terms)


def tfidf_score(query: str, text: str, corpus_size: int = 100) -> float:
    terms = query.lower().split()
    if not terms:
        return 1.0
    text_lower = text.lower()
    word_counts = defaultdict(int)
    for word in re.findall(r"\w+", text_lower):
        word_counts[word] += 1
    total_words = sum(word_counts.values()) or 1
    score = 0.0
    for term in terms:
        tf = word_counts.get(term, 0) / total_words
        idf = math.log(corpus_size / (1 + (1 if term in text_lower else 0)))
        score += tf * idf
    return score


def recency_score(created_str: str) -> float:
    try:
        created = datetime.strptime(created_str, "%Y-%m-%d")
        age_days = (datetime.now() - created).days
        return max(0.0, 1.0 - (age_days / 365.0))
    except ValueError:
        return 0.5


def search_memories(
    query=None, memory_type=None, category=None, project=None,
    limit=10, sort="relevance", older_than=None, brief=True,
) -> list:
    if not MEMORY_ROOT.exists():
        print(f"⚠️  Memory store not found at {MEMORY_ROOT}")
        return []

    results = []
    cutoff = datetime.now() - timedelta(days=older_than) if older_than else None
    search_root = MEMORY_ROOT

    for md_file in sorted(search_root.rglob("*.md")):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        fm = parse_frontmatter(text)

        # Filters
        if memory_type and memory_type != "all":
            if fm.get("type", str(md_file.parent.parent.name)) != memory_type:
                continue
        if category and fm.get("category", str(md_file.parent.name)) != category:
            continue
        if project and fm.get("project", "null") not in (project, f"{project}"):
            continue
        if cutoff:
            try:
                if datetime.strptime(fm.get("created", "2000-01-01"), "%Y-%m-%d") > cutoff:
                    continue
            except ValueError:
                pass

        score = 1.0
        if query:
            score = keyword_score(query, text)
            if score == 0.0:
                continue

        if sort == "recency":
            score = recency_score(fm.get("created", "2000-01-01"))

        results.append({
            "path": str(md_file.relative_to(MEMORY_ROOT.parent)),
            "full_path": str(md_file),
            "title": fm.get("title", md_file.stem),
            "type": fm.get("type", "unknown"),
            "category": fm.get("category", "unknown"),
            "project": fm.get("project", "null"),
            "tags": fm.get("tags", ""),
            "created": fm.get("created", ""),
            "confidence": fm.get("confidence", "high"),
            "score": round(score, 3),
            "summary": extract_summary(text, fm),
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def build_index():
    index = {"entries": {}, "tags": {}, "last_updated": datetime.now().isoformat()}
    count = 0
    for md_file in MEMORY_ROOT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        fm = parse_frontmatter(text)
        entry_id = fm.get("id", md_file.stem)
        index["entries"][entry_id] = {
            "path": str(md_file.relative_to(MEMORY_ROOT.parent)),
            "title": fm.get("title", md_file.stem),
            "type": fm.get("type", ""),
            "tags": fm.get("tags", ""),
            "created": fm.get("created", ""),
        }
        for tag in re.findall(r"[\w-]+", fm.get("tags", "")):
            index["tags"].setdefault(tag, []).append(entry_id)
        count += 1

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"✅ Index rebuilt: {count} entries indexed")


def print_stats():
    by_type = defaultdict(int)
    for md_file in MEMORY_ROOT.rglob("*.md"):
        try:
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            fm = parse_frontmatter(text)
            by_type[fm.get("type", "unknown")] += 1
        except Exception:
            pass
    total = sum(by_type.values())
    print(f"\n📊 Memory Store Stats ({total} total entries)")
    print("─" * 36)
    for t, c in sorted(by_type.items()):
        print(f"  {t:<15} {c:>4} entries")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search the OpenSite memory store")
    parser.add_argument("--query", default=None)
    parser.add_argument("--type", default=None, help="all | episodic | semantic | procedural | working")
    parser.add_argument("--category", default=None)
    parser.add_argument("--project", default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sort", default="relevance", choices=["relevance", "recency"])
    parser.add_argument("--older-than", type=int, default=None, help="Only entries older than N days")
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--stats", action="store_true")

    args = parser.parse_args()

    if args.rebuild_index:
        build_index()
        sys.exit(0)

    if args.stats:
        print_stats()
        sys.exit(0)

    results = search_memories(
        query=args.query,
        memory_type=args.type,
        category=args.category,
        project=args.project,
        limit=args.limit,
        sort=args.sort,
        older_than=args.older_than,
    )

    if not results:
        print("  No memories found matching your query.")
    else:
        for r in results:
            print(f"\n[{r['score']:.2f}] {r['path']}")
            print(f"  Title:    {r['title']}")
            print(f"  Tags:     {r['tags']}")
            print(f"  Created:  {r['created']}  |  Confidence: {r['confidence']}")
            print(f"  Summary:  {r['summary'][:120]}...")
