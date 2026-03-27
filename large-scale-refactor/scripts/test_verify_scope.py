#!/usr/bin/env python3
"""
Test suite for verify_scope.py script
"""

import unittest
import tempfile
import os
import subprocess
from pathlib import Path

class TestVerifyScope(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory for tests
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)
        
        # Initialize git repo
        subprocess.run(['git', 'init'], capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.email', 'test@test.com'], capture_output=True, check=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], capture_output=True, check=True)
    
    def tearDown(self):
        # Clean up
        os.chdir('/')
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def create_test_files(self):
        """Create test file structure"""
        # Create directory structure
        Path('src/components').mkdir(parents=True, exist_ok=True)
        Path('src/utils').mkdir(parents=True, exist_ok=True)
        Path('config').mkdir(parents=True, exist_ok=True)
        
        # Create files
        (Path('src/components') / 'Button.js').write_text('export const Button = () => <button>Click</button>')
        (Path('src/components') / 'Header.js').write_text('export const Header = () => <header>Header</header>')
        (Path('src/utils') / 'helpers.js').write_text('export const helper = () => {}')
        (Path('config') / 'app.config.js').write_text('export const config = {}')
        
        # Create initial commit
        subprocess.run(['git', 'add', '.'], capture_output=True, check=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], capture_output=True, check=True)
    
    def test_allowlist_parsing(self):
        """Test allowlist file parsing"""
        # Create allowlist
        allowlist_content = """# Refactoring Scope Allowlist
src/components/
src/utils/
*.js
"""
        Path('.refactor-scope-allowlist').write_text(allowlist_content)
        
        # Test the read_allowlist function by importing it
        import sys
        sys.path.insert(0, '/Users/jordanhudgens/code/dashtrack/opensite-skills/large-scale-refactor/scripts')
        from verify_scope import read_allowlist
        
        patterns = read_allowlist('.refactor-scope-allowlist')
        self.assertEqual(len(patterns), 3)
        self.assertIn('src/components/', patterns)
        self.assertIn('src/utils/', patterns)
        self.assertIn('*.js', patterns)
    
    def test_scope_compliance(self):
        """Test scope compliance checking"""
        self.create_test_files()
        
        # Modify some files (simulate refactoring)
        (Path('src/components') / 'Button.js').write_text('export const Button = () => <button>Click</button> // modified')
        (Path('src/utils') / 'helpers.js').write_text('export const helper = () => {} // modified')
        
        # Create allowlist
        allowlist_content = """# Refactoring Scope Allowlist
src/components/
src/utils/
"""
        Path('.refactor-scope-allowlist').write_text(allowlist_content)
        
        # Test scope checking
        import sys
        sys.path.insert(0, '/Users/jordanhudgens/code/dashtrack/opensite-skills/large-scale-refactor/scripts')
        from verify_scope import get_changed_files, check_scope_compliance
        
        changed_files = get_changed_files()
        self.assertEqual(len(changed_files), 2)
        
        out_of_scope = check_scope_compliance(changed_files, ['src/components/', 'src/utils/'])
        self.assertEqual(len(out_of_scope), 0)
        
        # Now test with an out-of-scope change
        (Path('config') / 'app.config.js').write_text('export const config = {} // modified')
        
        changed_files = get_changed_files()
        out_of_scope = check_scope_compliance(changed_files, ['src/components/', 'src/utils/'])
        self.assertEqual(len(out_of_scope), 1)
        self.assertIn('config/app.config.js', out_of_scope[0])
    
    def test_end_to_end_verification(self):
        """Test full verification script"""
        self.create_test_files()
        
        # Modify in-scope files
        (Path('src/components') / 'Button.js').write_text('export const Button = () => <button>Click</button> // modified')
        
        # Create allowlist
        allowlist_content = """# Refactoring Scope Allowlist
src/components/
src/utils/
"""
        Path('.refactor-scope-allowlist').write_text(allowlist_content)
        
        # Run verification script
        result = subprocess.run([
            'python', '/Users/jordanhudgens/code/dashtrack/opensite-skills/large-scale-refactor/scripts/verify_scope.py'
        ], capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn("All changed files are within approved scope", result.stdout)
        
        # Test with out-of-scope changes
        (Path('config') / 'app.config.js').write_text('export const config = {} // modified')
        
        result = subprocess.run([
            'python', '/Users/jordanhudgens/code/dashtrack/opensite-skills/large-scale-refactor/scripts/verify_scope.py', '--strict'
        ], capture_output=True, text=True)
        
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("SCOPE VIOLATION", result.stdout)

if __name__ == '__main__':
    unittest.main()
