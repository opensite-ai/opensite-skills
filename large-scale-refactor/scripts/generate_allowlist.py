#!/usr/bin/env python3
"""
Generate scope allowlist from refactoring spec.
Extracts IN SCOPE file patterns and creates .refactor-scope-allowlist file.
"""

import sys
import os
import re
import argparse
from pathlib import Path

def extract_scope_patterns(spec_content):
    """Extract IN SCOPE patterns from spec content."""
    patterns = []
    
    # Look for IN SCOPE section
    in_scope_section = False
    for line in spec_content.split('\n'):
        if 'IN SCOPE' in line or '## IN SCOPE' in line:
            in_scope_section = True
            continue
        
        if in_scope_section:
            # Stop at OUT OF SCOPE or next major section
            if ('OUT OF SCOPE' in line or '## OUT OF SCOPE' in line or 
                line.startswith('## ') or line.startswith('### ')):
                break
            
            # Extract file patterns
            if 'File types:' in line:
                # Extract file patterns like *.js, *.tsx
                file_patterns = re.findall(r'\*\.\w+', line)
                patterns.extend(file_patterns)
            
            if 'Directories:' in line:
                # Extract directory patterns
                dir_patterns = re.findall(r'src/\w+/|tests/|components/|hooks/', line)
                patterns.extend(dir_patterns)
            
            # Also look for explicit file/directory listings
            if line.strip().startswith('- ['):
                # Extract patterns from bullet points
                match = re.search(r'\[\] (.*?)( —|$)', line)
                if match:
                    pattern = match.group(1).strip()
                    if pattern and not pattern.startswith('File types:') and \
                       not pattern.startswith('Operations:') and \
                       not pattern.startswith('Directories:'):
                        patterns.append(pattern)
    
    return patterns

def read_spec_file(spec_path):
    """Read spec file content."""
    try:
        with open(spec_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        print(f"Error: Spec file not found at {spec_path}")
        sys.exit(1)

def write_allowlist(allowlist_path, patterns):
    """Write patterns to allowlist file."""
    try:
        with open(allowlist_path, 'w') as f:
            f.write("# Refactoring Scope Allowlist\n")
            f.write("# Generated from refactoring spec\n")
            f.write("# One pattern per line\n")
            f.write("# Use # for comments\n\n")
            
            for pattern in sorted(set(patterns)):  # Remove duplicates and sort
                if pattern:  # Skip empty patterns
                    f.write(f"{pattern}\n")
        
        print(f"✅ Allowlist written to {allowlist_path}")
        print(f"   Patterns: {len(patterns)} (unique: {len(set(patterns))})")
        
    except IOError as e:
        print(f"Error writing allowlist: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Generate scope allowlist from refactoring spec')
    parser.add_argument('spec_file', help='Path to refactoring spec file')
    parser.add_argument('--output', default='.refactor-scope-allowlist',
                       help='Output allowlist file path')
    
    args = parser.parse_args()
    
    print("=== Scope Allowlist Generator ===")
    print(f"Spec file: {args.spec_file}")
    print(f"Output: {args.output}")
    
    # Read spec
    spec_content = read_spec_file(args.spec_file)
    
    # Extract patterns
    patterns = extract_scope_patterns(spec_content)
    
    if not patterns:
        print("⚠️  No patterns found in spec. Check format.")
        print("   Expected format:")
        print("   - [x] File types: *.js, *.jsx")
        print("   - [x] Directories: src/, tests/")
        sys.exit(1)
    
    print(f"\nExtracted patterns:")
    for i, pattern in enumerate(sorted(set(patterns)), 1):
        print(f"  {i}. {pattern}")
    
    # Write allowlist
    write_allowlist(args.output, patterns)
    
    print(f"\n📋 Allowlist content:")
    try:
        with open(args.output, 'r') as f:
            content = f.read()
        print(content)
    except IOError:
        print("Could not read generated file")

if __name__ == '__main__':
    main()
