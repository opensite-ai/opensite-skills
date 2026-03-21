#!/usr/bin/env python3
"""Validate that a workflow brief markdown file includes the required headings."""

from pathlib import Path
import sys

REQUIRED = [
    "## Problem",
    "## Inputs and Context",
    "## Step Plan",
    "## Output Contract",
    "## Risks",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_workflow_brief.py <brief.md>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    text = path.read_text()
    missing = [heading for heading in REQUIRED if heading not in text]
    if missing:
        print("Missing headings:")
        for heading in missing:
            print(f"  - {heading}")
        return 1

    print("Workflow brief looks structurally complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
