#!/usr/bin/env python3
"""Validate a semantic UI builder JSON payload."""

from __future__ import annotations

import json
from pathlib import Path
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_builder_payload.py <payload.json>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    data = json.loads(path.read_text())
    errors = []
    if not isinstance(data.get("blockId"), str) or not data["blockId"].strip():
        errors.append("blockId must be a non-empty string")
    if not isinstance(data.get("props"), dict):
        errors.append("props must be an object")
    reasoning = data.get("reasoning")
    if reasoning is not None and not isinstance(reasoning, str):
        errors.append("reasoning must be a string when present")

    if errors:
        for error in errors:
            print(f"- {error}")
        return 1

    print("Builder payload looks structurally valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
