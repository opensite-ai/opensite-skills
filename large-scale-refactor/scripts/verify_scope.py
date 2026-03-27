#!/usr/bin/env python3
"""
Scope verification script for large-scale-refactor skill.
Validates that all changed files are within the approved scope.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def read_allowlist(allowlist_path):
    """Read the scope allowlist file."""
    try:
        with open(allowlist_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        print(f"Error: Allowlist file not found at {allowlist_path}")
        sys.exit(1)

def get_changed_files():
    """Get list of changed files from git."""
    try:
        result = subprocess.run(['git', 'diff', 'HEAD', '--name-only'],
                              capture_output=True, text=True, check=True)
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except subprocess.CalledProcessError as e:
        print(f"Error getting git diff: {e}")
        sys.exit(1)

def check_scope_compliance(changed_files, allowlist):
    """Check if all changed files are in the allowlist."""
    out_of_scope = []
    
    for file in changed_files:
        # Check if file matches any pattern in allowlist
        matched = False
        for pattern in allowlist:
            # Simple pattern matching - could be enhanced with fnmatch or regex
            if pattern in file or file.startswith(pattern.rstrip('/') + '/') or file == pattern:
                matched = True
                break
        
        if not matched:
            out_of_scope.append(file)
    
    return out_of_scope

def main():
    parser = argparse.ArgumentParser(description='Verify refactoring scope compliance')
    parser.add_argument('--allowlist', default='.refactor-scope-allowlist',
                       help='Path to scope allowlist file')
    parser.add_argument('--strict', action='store_true',
                       help='Exit with error code if any out-of-scope files found')
    
    args = parser.parse_args()
    
    print("=== Scope Verification ===")
    print(f"Allowlist: {args.allowlist}")
    
    # Read allowlist
    allowlist = read_allowlist(args.allowlist)
    print(f"Allowed patterns: {len(allowlist)}")
    for pattern in allowlist:
        print(f"  - {pattern}")
    
    # Get changed files
    changed_files = get_changed_files()
    print(f"\nChanged files: {len(changed_files)}")
    for file in changed_files:
        print(f"  - {file}")
    
    # Check compliance
    out_of_scope = check_scope_compliance(changed_files, allowlist)
    
    if out_of_scope:
        print(f"\n❌ SCOPE VIOLATION: {len(out_of_scope)} files out of scope:")
        for file in out_of_scope:
            print(f"  - {file}")
        
        if args.strict:
            sys.exit(1)
        else:
            print("\n(Continuing in non-strict mode)")
    else:
        print("\n✅ All changed files are within approved scope")
    
    # Additional checks
    print("\n=== Additional Verification ===")
    
    # Check for new files
    try:
        result = subprocess.run(['git', 'diff', 'HEAD', '--name-status'],
                              capture_output=True, text=True, check=True)
        new_files = [line.split('\t')[1] for line in result.stdout.split('\n') 
                    if line.startswith('A\t')]
        
        if new_files:
            print(f"New files created: {len(new_files)}")
            for file in new_files:
                print(f"  - {file}")
        else:
            print("No new files created")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not check for new files: {e}")
    
    # Check dependency files
    dep_files = ['package.json', 'package-lock.json', 'yarn.lock', 
                'Cargo.toml', 'Gemfile', 'Gemfile.lock']
    dep_changes = [f for f in changed_files if any(dep in f for dep in dep_files)]
    
    if dep_changes:
        print(f"Dependency files changed: {len(dep_changes)}")
        for file in dep_changes:
            print(f"  - {file}")
    else:
        print("No dependency files changed")

if __name__ == '__main__':
    main()
