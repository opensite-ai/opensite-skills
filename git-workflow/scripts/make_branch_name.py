#!/usr/bin/env python3
"""Generate a branch name using the OpenSite conventions."""

from __future__ import annotations

import re
import sys

ALLOWED = {"feature", "fix", "chore", "security", "release", "hotfix"}


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", slug)


def main() -> int:
    if len(sys.argv) < 3:
        print("Usage: make_branch_name.py <type> <description...>")
        return 1

    branch_type = sys.argv[1].lower()
    if branch_type not in ALLOWED:
        print(f"Unsupported branch type: {branch_type}")
        return 1

    description = slugify(" ".join(sys.argv[2:]))
    if not description:
        print("Description produced an empty slug.")
        return 1

    print(f"{branch_type}/{description}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
