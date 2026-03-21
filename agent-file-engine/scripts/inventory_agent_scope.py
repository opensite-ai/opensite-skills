#!/usr/bin/env python3
"""Inventory a repository for AGENTS.md coverage planning."""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".next",
    ".turbo",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "tmp",
    "vendor",
}

MANIFESTS = [
    "package.json",
    "pnpm-workspace.yaml",
    "turbo.json",
    "Cargo.toml",
    "Gemfile",
    "pyproject.toml",
    "go.mod",
]

DOC_CANDIDATES = [
    "README.md",
    "CLAUDE.md",
    "AGENTS.md",
]

HIGH_SIGNAL_PATTERNS = [
    ("components/blocks", "semantic block library with local serialization and registry rules"),
    ("src/services/orchestration", "workflow/orchestration subsystem with specialized invariants"),
    ("src/services/vectorization", "vectorization pipeline with specialized processing rules"),
    ("app/services/ai", "AI service layer with provider, webhook, or processor constraints"),
    ("app/services/site_builder_manager", "site builder subsystem with generation and styling rules"),
    ("app/jobs", "background-job conventions may differ from request-time code"),
    ("workers", "worker processes often need their own runtime and retry rules"),
    ("jobs", "job execution paths often need idempotency and queue-specific rules"),
]

SOURCE_EXTENSIONS = {
    ".rs",
    ".rb",
    ".py",
    ".go",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
}


def source_file_count(path: Path) -> int:
    count = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            if Path(file_name).suffix in SOURCE_EXTENSIONS:
                count += 1
    return count


def language_counts(repo: Path) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file_name in files:
            suffix = Path(file_name).suffix.lower()
            if suffix in SOURCE_EXTENSIONS:
                counter[suffix] += 1
    return dict(sorted(counter.items()))


def gather_candidates(repo: Path) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for rel_path, reason in HIGH_SIGNAL_PATTERNS:
        path = repo / rel_path
        if path.exists() and path.is_dir():
            count = source_file_count(path)
            if count:
                candidates.append(
                    {
                        "path": rel_path,
                        "reason": reason,
                        "source_files": count,
                        "existing_agents": (path / "AGENTS.md").exists(),
                    }
                )

    for child in ("apps", "packages", "libs", "modules", "services"):
        root = repo / child
        if not root.exists() or not root.is_dir():
            continue
        for item in sorted(root.iterdir()):
            if not item.is_dir() or item.name in SKIP_DIRS:
                continue
            count = source_file_count(item)
            if count >= 12:
                candidates.append(
                    {
                        "path": str(item.relative_to(repo)),
                        "reason": f"standalone {child[:-1] if child.endswith('s') else child} subtree with meaningful code volume",
                        "source_files": count,
                        "existing_agents": (item / "AGENTS.md").exists(),
                    }
                )

    deduped = {}
    for candidate in candidates:
        deduped[candidate["path"]] = candidate
    return sorted(deduped.values(), key=lambda item: (item["path"]))


def build_report(repo: Path) -> dict[str, object]:
    manifests = [name for name in MANIFESTS if (repo / name).exists()]
    top_docs = [name for name in DOC_CANDIDATES if (repo / name).exists()]
    top_docs.extend(
        sorted(
            str(path.relative_to(repo))
            for path in (repo / "docs").glob("*.md")
            if path.is_file()
        )
        if (repo / "docs").exists()
        else []
    )

    agents_files = sorted(str(path.relative_to(repo)) for path in repo.rglob("AGENTS.md"))

    return {
        "repo": str(repo),
        "manifests": manifests,
        "top_docs": top_docs,
        "languages": language_counts(repo),
        "agents_files": agents_files,
        "candidate_nested_dirs": gather_candidates(repo),
    }


def print_markdown(report: dict[str, object]) -> None:
    print(f"# AGENTS coverage inventory for `{report['repo']}`")
    print()
    print("## Manifests")
    for manifest in report["manifests"]:
        print(f"- `{manifest}`")
    if not report["manifests"]:
        print("- none found")

    print()
    print("## Top docs")
    for doc in report["top_docs"]:
        print(f"- `{doc}`")
    if not report["top_docs"]:
        print("- none found")

    print()
    print("## Existing AGENTS.md files")
    for path in report["agents_files"]:
        print(f"- `{path}`")
    if not report["agents_files"]:
        print("- none found")

    print()
    print("## Languages")
    for suffix, count in report["languages"].items():
        print(f"- `{suffix}`: {count}")
    if not report["languages"]:
        print("- no recognized source files found")

    print()
    print("## Candidate nested directories")
    for candidate in report["candidate_nested_dirs"]:
        status = "existing AGENTS.md" if candidate["existing_agents"] else "candidate"
        print(
            f"- `{candidate['path']}` - {status}; {candidate['source_files']} source files; {candidate['reason']}"
        )
    if not report["candidate_nested_dirs"]:
        print("- no strong nested candidates detected")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inventory a repository to plan root and nested AGENTS.md coverage.",
    )
    parser.add_argument("repo", nargs="?", default=".", help="Repository root to inspect")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    if not repo.exists() or not repo.is_dir():
        print(f"Not a directory: {repo}")
        return 1

    report = build_report(repo)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_markdown(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
