# Paleae Cookbook

This page provides practical, copy-paste-ready recipes for common Paleae workflows.

[< Back to Wiki Home](Home)

## Table of Contents
- [Snapshot Recently Changed Files](#snapshot-recently-changed-files)
- [Compare Two Snapshots](#compare-two-snapshots)
- [Generate a Codebase Report](#generate-a-codebase-report)
- [Filter Snapshot for a Token Budget](#filter-snapshot-for-a-token-budget)

---

## Snapshot Recently Changed Files

**Goal:** Create a snapshot containing only the files that have been modified in the last 7 days.

**Use Case:** Quickly providing context to an AI about recent development activity without including the entire codebase.

**Method:** This shell script uses `git log` to find the files and pipes them into Paleae's `--include` filter.

```bash
#!/bin/bash
# recent_changes.sh

# 1. Get a list of files changed in the last 7 days, separated by |
RECENT_FILES=$(git log --since="7 days ago" --name-only --pretty=format: | sort -u | tr '\n' '|')

# 2. Remove the trailing | if the list is not empty
if [ -n "$RECENT_FILES" ]; then
    PATTERN="(${RECENT_FILES%|})"
    
    # 3. Create the snapshot using the generated pattern
    python3 paleae.py --include "$PATTERN" -o recent_changes.json
    
    echo "Snapshot of recently changed files created in recent_changes.json"
else
    echo "No recent changes found."
fi
```

---

## Compare Two Snapshots

**Goal:** Identify the differences between two snapshot files.

**Use Case:** Understanding what has changed between two points in time, such as before and after a major refactoring.

**Method:** This Python script loads two snapshot files and compares the file paths and their SHA-256 hashes.

```python
#!/usr/bin/env python3
# compare_snapshots.py

import json
import sys

def compare_snapshots(old_path, new_path):
    """Compare two snapshots and print a summary of changes."""
    
    with open(old_path) as f:
        old_data = json.load(f)
    with open(new_path) as f:
        new_data = json.load(f)
    
    old_files = {f["path"]: f["sha256"] for f in old_data["files"]}
    new_files = {f["path"]: f["sha256"] for f in new_data["files"]}
    
    added = set(new_files.keys()) - set(old_files.keys())
    removed = set(old_files.keys()) - set(new_files.keys())
    
    modified = {
        path for path in old_files.keys() & new_files.keys() 
        if old_files[path] != new_files[path]
    }
    
    print(f"--- Snapshot Comparison ---")
    print(f"Old: {old_path} ({old_data['meta']['summary']['total_files']} files)")
    print(f"New: {new_path} ({new_data['meta']['summary']['total_files']} files)")
    print("---------------------------")
    print(f"Added:    {len(added)}")
    print(f"Removed:  {len(removed)}")
    print(f"Modified: {len(modified)}")

    if added:
        print("\n--- Added Files ---")
        for path in sorted(added):
            print(f"+ {path}")

    if modified:
        print("\n--- Modified Files ---")
        for path in sorted(modified):
            print(f"~ {path}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 compare_snapshots.py <old_snapshot.json> <new_snapshot.json>")
        sys.exit(1)
    
    compare_snapshots(sys.argv[1], sys.argv[2])
```

---

## Generate a Codebase Report

**Goal:** Create a high-level Markdown report from a snapshot.

**Use Case:** Generating quick, shareable documentation about the project's structure and composition.

**Method:** This Python script processes a snapshot file and prints a Markdown-formatted report to the console.

```python
#!/usr/bin/env python3
# generate_report.py

import json
from collections import defaultdict
import sys

def generate_report(snapshot_path):
    """Analyzes a snapshot and prints a Markdown report."""
    with open(snapshot_path) as f:
        data = json.load(f)

    by_ext = defaultdict(lambda: {'count': 0, 'chars': 0})
    for file_obj in data['files']:
        ext = '.' + file_obj['path'].split('.')[-1] if '.' in file_obj['path'] else 'no_extension'
        by_ext[ext]['count'] += 1
        by_ext[ext]['chars'] += file_obj['size_chars']

    print(f"# Codebase Report for {data['meta']['root_directory']}")
    print(f"_Generated on {data['meta']['timestamp']}_")
    print("\n## Summary")
    print(f"- **Total Files:** {data['meta']['summary']['total_files']}")
    print(f"- **Total Characters:** {data['meta']['summary']['total_chars']:,}")
    print(f"- **Estimated Tokens:** {data['meta']['summary']['estimated_tokens']:,}")

    print("\n## File Types")
    print("| Extension | File Count | Total Chars |")
    print("| :--- | :--- | :--- |")
    for ext, stats in sorted(by_ext.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f"| {ext} | {stats['count']} | {stats['chars']:,} |")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 generate_report.py <snapshot.json>")
        sys.exit(1)

    generate_report(sys.argv[1])
```

---

## Filter Snapshot for a Token Budget

**Goal:** Reduce a snapshot's size to fit within an LLM's context window.

**Use Case:** Ensuring your snapshot doesn't exceed the token limit of models like GPT-4 (e.g., 128k tokens) or Claude 3 (e.g., 200k tokens).

**Method:** This Python script loads a snapshot, removes files until it fits the budget, prioritizing source code over other file types.

```python
#!/usr/bin/env python3
# filter_by_tokens.py

import json
import sys

def filter_for_budget(snapshot_path, max_tokens=100000):
    """Filters a snapshot to fit within a specified token budget."""
    with open(snapshot_path) as f:
        data = json.load(f)

    if data['meta']['summary']['estimated_tokens'] <= max_tokens:
        print("Snapshot is already within the token budget.")
        return

    # Prioritize file types (e.g., source code > docs > configs)
    priority_exts = ['.py', '.js', '.ts', '.go', '.rs', '.java', '.md', '.toml', '.yaml']
    
    # Sort files by priority and then by size (smallest first)
    def sort_key(file_obj):
        ext = '.' + file_obj['path'].split('.')[-1] if '.' in file_obj['path'] else ''
        priority = priority_exts.index(ext) if ext in priority_exts else len(priority_exts)
        return (priority, file_obj['estimated_tokens'])

    sorted_files = sorted(data['files'], key=sort_key)

    # Fill the budget with the highest priority files
    selected_files = []
    token_count = 0
    for file_obj in sorted_files:
        if token_count + file_obj['estimated_tokens'] <= max_tokens:
            selected_files.append(file_obj)
            token_count += file_obj['estimated_tokens']

    # Create the new, smaller snapshot
    data['files'] = selected_files
    data['meta']['summary']['total_files'] = len(selected_files)
    data['meta']['summary']['total_chars'] = sum(f['size_chars'] for f in selected_files)
    data['meta']['summary']['estimated_tokens'] = token_count

    output_path = snapshot_path.replace('.json', '_filtered.json')
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Filtered snapshot saved to {output_path}")
    print(f"New token count: {token_count:,} / {max_tokens:,}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 filter_by_tokens.py <snapshot.json> <max_tokens>")
        sys.exit(1)

    filter_for_budget(sys.argv[1], int(sys.argv[2]))
```

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
