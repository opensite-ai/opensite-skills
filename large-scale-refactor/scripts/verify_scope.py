#!/usr/bin/env python3
"""
Scope verification script for large-scale-refactor skill.
Validates that all changed files are within the approved scope allowlist.

Usage:
    python verify_scope.py                              # report only
    python verify_scope.py --strict                     # exit 1 on any violation
    python verify_scope.py --allowlist custom.txt       # use a different allowlist
    python verify_scope.py --base HEAD~1                # compare against a specific ref
"""

import argparse
import fnmatch
import os
import subprocess
import sys
from pathlib import Path


def read_allowlist(allowlist_path: str) -> list[str]:
    """Read patterns from the scope allowlist file, skipping comments and blanks."""
    try:
        with open(allowlist_path, "r") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]
    except FileNotFoundError:
        print(f"Error: Allowlist file not found at {allowlist_path}")
        sys.exit(1)


def get_changed_files(base_ref: str = "HEAD") -> list[str]:
    """Return the list of files changed relative to *base_ref*."""
    try:
        result = subprocess.run(
            ["git", "diff", base_ref, "--name-only"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e}")
        sys.exit(1)


def _file_matches_pattern(file: str, pattern: str) -> bool:
    """
    Return True when *file* is covered by *pattern*.

    Three match strategies are tried in order:

    1. **Directory prefix** — pattern ends with ``/``, e.g. ``src/components/``.
       Matches any file whose path starts with that prefix.

    2. **Glob** — pattern contains ``*`` or ``?``, e.g. ``*.js``, ``src/**/*.tsx``.
       Matched against the full path AND the bare filename so that ``*.js``
       covers ``src/components/Button.js`` without requiring ``**/*.js``.

    3. **Exact** — literal path equality, e.g. ``config/settings.py``.
    """
    # 1. Directory prefix (trailing slash required — prevents false prefix matches)
    if pattern.endswith("/"):
        if file.startswith(pattern):
            return True

    # 2. Glob (fnmatch handles *, ?, [...] character classes)
    if "*" in pattern or "?" in pattern or ("[" in pattern and "]" in pattern):
        # Match against full path
        if fnmatch.fnmatch(file, pattern):
            return True
        # Also match basename alone so '*.js' catches 'src/foo/bar.js'
        if fnmatch.fnmatch(os.path.basename(file), pattern):
            return True
        return False

    # 3. Exact match
    return file == pattern


def check_scope_compliance(changed_files: list[str], allowlist: list[str]) -> list[str]:
    """
    Return the subset of *changed_files* that are NOT covered by any
    pattern in *allowlist*.  An empty list means full scope compliance.
    """
    out_of_scope = []
    for file in changed_files:
        if not any(_file_matches_pattern(file, pattern) for pattern in allowlist):
            out_of_scope.append(file)
    return out_of_scope


def get_new_files(base_ref: str = "HEAD") -> list[str]:
    """Return files that were *added* (status A) relative to *base_ref*."""
    try:
        result = subprocess.run(
            ["git", "diff", base_ref, "--name-status"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [
            line.split("\t", 1)[1].strip()
            for line in result.stdout.splitlines()
            if line.startswith("A\t")
        ]
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not retrieve new-file list: {e}", file=sys.stderr)
        return []


def get_dependency_changes(changed_files: list[str]) -> list[str]:
    """Return any dependency-manifest files present in *changed_files*."""
    dep_manifests = {
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.toml",
        "Cargo.lock",
        "Gemfile",
        "Gemfile.lock",
        "pyproject.toml",
        "requirements.txt",
        "go.mod",
        "go.sum",
    }
    return [f for f in changed_files if os.path.basename(f) in dep_manifests]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that all changed files are within the approved refactoring scope."
    )
    parser.add_argument(
        "--allowlist",
        default=".refactor-scope-allowlist",
        help="Path to the scope allowlist file (default: .refactor-scope-allowlist)",
    )
    parser.add_argument(
        "--base",
        default="HEAD",
        help="Git ref to diff against (default: HEAD)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any out-of-scope files or violations are found",
    )
    args = parser.parse_args()

    print("=== Scope Verification ===")
    print(f"Allowlist : {args.allowlist}")
    print(f"Base ref  : {args.base}")

    allowlist = read_allowlist(args.allowlist)
    print(f"Allowed patterns ({len(allowlist)}):")
    for pattern in allowlist:
        print(f"  - {pattern}")

    changed_files = get_changed_files(args.base)
    print(f"\nChanged files ({len(changed_files)}):")
    for f in changed_files:
        print(f"  - {f}")

    # ── Scope compliance ────────────────────────────────────────────────────
    out_of_scope = check_scope_compliance(changed_files, allowlist)
    violation = False

    if out_of_scope:
        print(
            f"\n❌ SCOPE VIOLATION: {len(out_of_scope)} file(s) outside approved scope:"
        )
        for f in out_of_scope:
            print(f"  - {f}")
        violation = True
    else:
        print("\n✅ All changed files are within approved scope")

    # ── New file audit ──────────────────────────────────────────────────────
    print("\n=== New File Audit ===")
    new_files = get_new_files(args.base)
    if new_files:
        print(
            f"⚠️  New files created ({len(new_files)}) — verify these are spec-defined outputs:"
        )
        for f in new_files:
            print(f"  - {f}")
    else:
        print("✅ No new files created")

    # ── Dependency check ────────────────────────────────────────────────────
    print("\n=== Dependency Check ===")
    dep_changes = get_dependency_changes(changed_files)
    if dep_changes:
        print(
            f"⚠️  Dependency manifest(s) modified ({len(dep_changes)}) — verify these changes are spec-approved:"
        )
        for f in dep_changes:
            print(f"  - {f}")
        violation = True
    else:
        print("✅ No dependency manifests modified")

    # ── Final result ────────────────────────────────────────────────────────
    print()
    if violation:
        print("⚠️  One or more checks require human review.")
        if args.strict:
            sys.exit(1)
        else:
            print("   (Running in non-strict mode — exiting 0)")
    else:
        print("✅ All checks passed. Scope is clean.")


if __name__ == "__main__":
    main()
