#!/usr/bin/env python3
"""
Generate scope allowlist from a refactoring spec file.

Reads the **IN SCOPE** section of a TASK_SPEC.md (or any spec file that follows
the large-scale-refactor template) and writes a .refactor-scope-allowlist file
containing one pattern per line.  The allowlist is consumed by verify_scope.py.

Supported pattern types extracted from IN SCOPE checked items:
  - Glob patterns   : *.js  *.tsx  **/*.py
  - Directory paths : src/  app/routes/  lib/
  - File paths      : config/settings.py  Cargo.toml
  - Bare extensions : .js  .tsx  (converted to *.ext)

Usage:
    python generate_allowlist.py TASK_SPEC.md
    python generate_allowlist.py TASK_SPEC.md --output .refactor-scope-allowlist
    python generate_allowlist.py TASK_SPEC.md --dry-run
"""

import argparse
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def _extract_patterns_from_text(raw: str) -> list[str]:
    """
    Pull every usable scope pattern out of a single IN SCOPE item's text.

    Returns a deduplicated list of patterns in insertion order.
    """
    found: list[str] = []

    # 1. Glob patterns that already contain a wildcard: *.js  **/*.tsx  src/**
    globs = re.findall(r"[\w\-\./]*\*[\w\-\./\*]*", raw)
    found.extend(globs)

    # 2. Directory-or-file paths: tokens containing at least one '/'
    #    Covers:  src/components/  app/routes/  lib/auth.py  tests/
    #    Excludes pure prose like "No logic changes" that has no slash.
    paths = re.findall(r"[\w\-\.][\w\-\./]*(?:/[\w\-\./]*)+/?", raw)
    for p in paths:
        # Normalise: if it ends with a word char and is clearly a directory
        # segment (no extension), add a trailing slash for clarity.
        if p and not p.endswith("/") and "." not in Path(p).name:
            p = p + "/"
        found.append(p)

    # 3. Bare extensions like .js or .tsx (not already captured as a glob)
    bare_ext = re.findall(r"(?<!\w)\.([\w]+)(?!\w)", raw)
    for ext in bare_ext:
        found.append(f"*.{ext}")

    return list(dict.fromkeys(p for p in found if p))  # preserve order, deduplicate


def extract_scope_patterns(spec_content: str) -> list[str]:
    """
    Parse *spec_content* and return all scope patterns from the IN SCOPE block.

    Understands two formats for the section header:
      **IN SCOPE** (agent may touch):   ← SKILL.md template bold marker
      ## IN SCOPE                       ← plain markdown heading

    The block ends at the first OUT OF SCOPE marker or the next ## heading.

    Only lines that are *checked* items (``- [x]`` or ``- [X]``) contribute
    patterns; unchecked items (``- [ ]``) are skipped so a partially-filled
    spec doesn't produce a misleadingly small allowlist.  If no checked items
    are found at all, *all* bullet items in the block are used as a fallback
    so a brand-new spec with empty checkboxes still produces a useful allowlist.
    """
    patterns: list[str] = []
    in_scope = False
    checked_lines: list[str] = []
    all_bullet_lines: list[str] = []

    for line in spec_content.splitlines():
        # ── Detect section start ──────────────────────────────────────────
        if re.search(r"\*\*IN SCOPE\*\*|^#+\s*IN SCOPE", line, re.IGNORECASE):
            in_scope = True
            continue

        # ── Detect section end ────────────────────────────────────────────
        if in_scope:
            if re.search(
                r"\*\*OUT OF SCOPE\*\*|^#+\s*OUT OF SCOPE|^##\s+\S",
                line,
                re.IGNORECASE,
            ):
                break

            # Checked item:   - [x] ...  or  - [X] ...
            checked_match = re.match(r"\s*-\s*\[[xX]\]\s*(.*)", line)
            if checked_match:
                raw = checked_match.group(1).strip()
                checked_lines.append(raw)
                all_bullet_lines.append(raw)
                continue

            # Unchecked item: - [ ] ...
            unchecked_match = re.match(r"\s*-\s*\[\s\]\s*(.*)", line)
            if unchecked_match:
                all_bullet_lines.append(unchecked_match.group(1).strip())
                continue

            # Plain bullet (no checkbox): - File types: *.js ...
            plain_match = re.match(r"\s*[-*]\s+(.*)", line)
            if plain_match:
                all_bullet_lines.append(plain_match.group(1).strip())

    # Use checked items if any exist; fall back to all bullets otherwise.
    source_lines = checked_lines if checked_lines else all_bullet_lines

    for text in source_lines:
        patterns.extend(_extract_patterns_from_text(text))

    # Final deduplication preserving insertion order
    return list(dict.fromkeys(p for p in patterns if p))


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------


def read_spec_file(spec_path: str) -> str:
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Spec file not found: {spec_path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"Error reading spec file: {e}", file=sys.stderr)
        sys.exit(1)


def write_allowlist(allowlist_path: str, patterns: list[str]) -> None:
    header = (
        "# Refactoring Scope Allowlist\n"
        "# Generated by generate_allowlist.py from refactoring spec\n"
        "#\n"
        "# Pattern rules (interpreted by verify_scope.py):\n"
        "#   src/components/   — directory prefix (trailing slash)\n"
        "#   *.js              — glob matched against full path and basename\n"
        "#   config/app.py     — exact file path\n"
        "#\n"
        "# Edit this file to adjust scope before running verify_scope.py.\n\n"
    )
    try:
        with open(allowlist_path, "w", encoding="utf-8") as f:
            f.write(header)
            for pattern in sorted(set(patterns)):
                if pattern:
                    f.write(f"{pattern}\n")
    except OSError as e:
        print(f"Error writing allowlist: {e}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a .refactor-scope-allowlist from a TASK_SPEC.md file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("spec_file", help="Path to the refactoring spec (TASK_SPEC.md)")
    parser.add_argument(
        "--output",
        default=".refactor-scope-allowlist",
        help="Destination allowlist file (default: .refactor-scope-allowlist)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print extracted patterns without writing any file",
    )
    args = parser.parse_args()

    print("=== Scope Allowlist Generator ===")
    print(f"Spec file : {args.spec_file}")
    if not args.dry_run:
        print(f"Output    : {args.output}")

    spec_content = read_spec_file(args.spec_file)
    patterns = extract_scope_patterns(spec_content)

    if not patterns:
        print(
            "\n⚠️  No scope patterns found in spec.\n"
            "   Make sure the spec contains an IN SCOPE section with checked items:\n\n"
            "   **IN SCOPE** (agent may touch):\n"
            "   - [x] File types: *.js, *.jsx\n"
            "   - [x] Directories: src/components/, src/utils/\n",
            file=sys.stderr,
        )
        sys.exit(1)

    unique_patterns = sorted(set(patterns))
    print(f"\nExtracted {len(unique_patterns)} unique pattern(s):")
    for i, pattern in enumerate(unique_patterns, 1):
        print(f"  {i:>3}. {pattern}")

    if args.dry_run:
        print("\n(Dry run — no file written)")
        return

    write_allowlist(args.output, patterns)
    print(f"\n✅ Allowlist written to: {args.output}")

    # Echo back what was written
    try:
        content = Path(args.output).read_text(encoding="utf-8")
        print("\n--- allowlist contents ---")
        print(content.rstrip())
        print("--- end ---")
    except OSError:
        pass


if __name__ == "__main__":
    main()
