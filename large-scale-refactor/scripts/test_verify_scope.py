#!/usr/bin/env python3
"""
Test suite for verify_scope.py script.

Run from anywhere — all paths are resolved relative to this file's location.

    python -m pytest scripts/test_verify_scope.py -v
    # or
    python scripts/test_verify_scope.py
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Dynamic path resolution — no hardcoded machine paths
# ---------------------------------------------------------------------------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
VERIFY_SCOPE = os.path.join(SCRIPTS_DIR, "verify_scope.py")

# Make the scripts directory importable so we can import verify_scope directly
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)


class TestVerifyScope(unittest.TestCase):
    def setUp(self):
        # Create a fresh temporary directory and initialise a git repo inside it
        self.test_dir = tempfile.mkdtemp()
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        subprocess.run(["git", "init"], capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], capture_output=True, check=True
        )

    def tearDown(self):
        os.chdir(self.original_dir)
        import shutil

        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_test_files(self):
        """Create a minimal file tree and an initial commit."""
        Path("src/components").mkdir(parents=True, exist_ok=True)
        Path("src/utils").mkdir(parents=True, exist_ok=True)
        Path("config").mkdir(parents=True, exist_ok=True)

        (Path("src/components") / "Button.js").write_text(
            "export const Button = () => <button>Click</button>"
        )
        (Path("src/components") / "Header.js").write_text(
            "export const Header = () => <header>Header</header>"
        )
        (Path("src/utils") / "helpers.js").write_text("export const helper = () => {}")
        (Path("config") / "app.config.js").write_text("export const config = {}")

        subprocess.run(["git", "add", "."], capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], capture_output=True, check=True
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_allowlist_parsing(self):
        """read_allowlist() returns the correct patterns from an allowlist file."""
        allowlist_content = (
            "# Refactoring Scope Allowlist\nsrc/components/\nsrc/utils/\n*.js\n"
        )
        Path(".refactor-scope-allowlist").write_text(allowlist_content)

        from verify_scope import read_allowlist

        patterns = read_allowlist(".refactor-scope-allowlist")

        self.assertEqual(len(patterns), 3)
        self.assertIn("src/components/", patterns)
        self.assertIn("src/utils/", patterns)
        self.assertIn("*.js", patterns)

    def test_scope_compliance_all_in_scope(self):
        """check_scope_compliance() reports no violations when all files are in scope."""
        self._create_test_files()

        (Path("src/components") / "Button.js").write_text(
            "export const Button = () => <button>Click</button> // modified"
        )
        (Path("src/utils") / "helpers.js").write_text(
            "export const helper = () => {} // modified"
        )

        from verify_scope import check_scope_compliance, get_changed_files

        changed_files = get_changed_files()
        self.assertEqual(len(changed_files), 2)

        out_of_scope = check_scope_compliance(
            changed_files, ["src/components/", "src/utils/"]
        )
        self.assertEqual(len(out_of_scope), 0)

    def test_scope_compliance_out_of_scope_detected(self):
        """check_scope_compliance() flags files that fall outside the allowlist."""
        self._create_test_files()

        # Modify only an out-of-scope file
        (Path("config") / "app.config.js").write_text(
            "export const config = {} // modified"
        )

        from verify_scope import check_scope_compliance, get_changed_files

        changed_files = get_changed_files()
        out_of_scope = check_scope_compliance(
            changed_files, ["src/components/", "src/utils/"]
        )

        self.assertEqual(len(out_of_scope), 1)
        self.assertIn("config/app.config.js", out_of_scope)

    def test_glob_pattern_matching(self):
        """check_scope_compliance() must handle *.ext glob patterns correctly."""
        self._create_test_files()

        # Modify a .js file — an allowlist entry of '*.js' should match it
        (Path("src/components") / "Button.js").write_text(
            "export const Button = () => <button>Click</button> // modified"
        )

        from verify_scope import check_scope_compliance, get_changed_files

        changed_files = get_changed_files()

        # '*.js' glob must match 'src/components/Button.js'
        out_of_scope = check_scope_compliance(changed_files, ["*.js"])
        self.assertEqual(
            len(out_of_scope),
            0,
            msg="'*.js' glob pattern failed to match src/components/Button.js — "
            "check_scope_compliance() must use fnmatch, not a plain 'in' test.",
        )

    def test_end_to_end_within_scope(self):
        """verify_scope.py exits 0 when all changed files are within the allowlist."""
        self._create_test_files()

        (Path("src/components") / "Button.js").write_text(
            "export const Button = () => <button>Click</button> // modified"
        )

        Path(".refactor-scope-allowlist").write_text(
            "# Refactoring Scope Allowlist\nsrc/components/\nsrc/utils/\n"
        )

        result = subprocess.run(
            ["python", VERIFY_SCOPE],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("All changed files are within approved scope", result.stdout)

    def test_end_to_end_scope_violation_strict(self):
        """verify_scope.py exits non-zero in --strict mode when a violation is found."""
        self._create_test_files()

        # Touch an out-of-scope file
        (Path("config") / "app.config.js").write_text(
            "export const config = {} // modified"
        )

        Path(".refactor-scope-allowlist").write_text(
            "# Refactoring Scope Allowlist\nsrc/components/\nsrc/utils/\n"
        )

        result = subprocess.run(
            ["python", VERIFY_SCOPE, "--strict"],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCOPE VIOLATION", result.stdout)

    def test_end_to_end_scope_violation_non_strict(self):
        """verify_scope.py exits 0 in non-strict mode even when violations exist."""
        self._create_test_files()

        (Path("config") / "app.config.js").write_text(
            "export const config = {} // non-strict violation"
        )

        Path(".refactor-scope-allowlist").write_text(
            "# Refactoring Scope Allowlist\nsrc/components/\n"
        )

        result = subprocess.run(
            ["python", VERIFY_SCOPE],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("SCOPE VIOLATION", result.stdout)


if __name__ == "__main__":
    unittest.main()
