# Advanced Usage

This page covers power-user workflows and advanced integration patterns for Paleae.

[< Back to Wiki Home](Home)

## Workflow Automation

### GitHub Actions
You can automate snapshot creation on every push using a GitHub Actions workflow. This is a key feature discussed in the [Integration Guide](Integration-Guide).

```yaml
# .github/workflows/snapshot.yml
name: Create Code Snapshot
on: [push]
jobs:
  snapshot:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v4
    - name: Download and Run Paleae
      run: |
        curl -fsSL https://raw.githubusercontent.com/PaulTiffany/paleae/main/paleae.py -o paleae.py
        python paleae.py --profile ai_optimized -f jsonl -o snapshot.jsonl
    - uses: actions/upload-artifact@v3
      with:
        name: code-snapshot
        path: snapshot.jsonl
```

### Pre-commit Hook
Automatically create a snapshot before each commit to track changes. This pattern is also covered in the [Integration Guide](Integration-Guide).
```bash
#!/bin/sh
# .git/hooks/pre-commit
python paleae.py --profile ai_optimized -o .git/snapshot_$(date +%Y%m%d).json
```

## Large Repository Strategies

### Chunked Processing
For massive repositories, process different parts separately and combine them later. This is a useful technique for managing memory, as noted in the [FAQ](FAQ).
```bash
python paleae.py --include "^src/core/" -f jsonl -o core.jsonl
python paleae.py --include "^src/utils/" -f jsonl -o utils.jsonl
```

### Selective Scanning
Focus only on recently changed files to speed up processing.
```bash
# Get files changed in the last 7 days and create a snapshot
RECENT_FILES=$(git log --since="7 days ago" --name-only --pretty=format: | sort -u)
python paleae.py --include "($(echo $RECENT_FILES | tr ' ' '|'))" -o recent.json
```

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
