# Usage Guide

This guide covers all command-line options for Paleae.

[< Back to Wiki Home](Home)

## Command Syntax
```bash
python paleae.py [directory] [options]
```

## Basic Options

- **`directory`**: The directory to snapshot. Defaults to the current directory.
- **`-o, --out`**: Specify the output file name. Defaults to `repo_snapshot.json`.
- **`-f, --format`**: The output format. Can be `json` (default) or `jsonl`. See the [Output Format](Output-Format) guide for details on the structure.

## Filtering Options

- **`--profile`**: Use a built-in filtering profile. See the [Configuration](Configuration) guide for a full explanation of profiles.
  - `minimal`: Includes most text files but skips common artifacts.
  - `ai_optimized`: Focuses on source code and key documentation for AI analysis.
- **`--include`**: A regex pattern to **include** files. Can be used multiple times.
- **`--exclude`**: A regex pattern to **exclude** files. Can be used multiple times.

For a detailed guide on how these filters work together, see the [Configuration](Configuration) page.

## Common Workflows

### AI Code Analysis
Create a clean, focused snapshot for analysis by an LLM.
```bash
python paleae.py --profile ai_optimized -o for_ai.json
```

### Documentation Generation
Snapshot only documentation and configuration files.
```bash
python paleae.py --include "\.(md|rst|toml|yaml)$" -o docs_and_config.json
```

### Large Repositories
Use JSONL format and selective filtering for better performance on large codebases, as discussed in [Advanced Usage](Advanced-Usage).
```bash
python paleae.py -f jsonl --include "^src/core/" -o large_repo_core.jsonl
```

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
