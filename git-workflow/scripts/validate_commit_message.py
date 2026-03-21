#!/usr/bin/env python3
"""Validate the repo's conventional commit format."""

from __future__ import annotations

import re
import sys

TYPES = "feat|fix|refactor|docs|test|chore|perf|style|ci|build"
PATTERN = re.compile(rf"^({TYPES}): [A-Z][^.\n]{{1,70}}$")


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: validate_commit_message.py "type: Title"')
        return 1

    message = sys.argv[1].strip()
    if not PATTERN.match(message):
        print("Invalid commit message.")
        print("Expected: <type>: <Sentence case title without trailing period>")
        return 1

    print("Commit message format looks good.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
