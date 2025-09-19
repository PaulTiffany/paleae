# API Reference

This document provides an overview of Paleae's programmatic interface for developers who want to extend or integrate it.

[< Back to Wiki Home](Home)

## Programmatic Usage
Paleae is a single-file module that can be imported directly. This allows you to integrate its file collection and snapshot generation capabilities into your own Python scripts.

### Core Functions

- **`collect_files()`**: The core function for gathering file paths. It uses the same powerful filtering logic as the CLI, accepting compiled regex patterns for includes, excludes, and ignore rules. See the [Configuration](Configuration) guide for more on filtering patterns.

- **`build_snapshot()`**: Takes a list of file paths and constructs the main snapshot dictionary, including the `meta` and `files` sections. The structure of this dictionary is detailed in the [Output Format](Output-Format) guide.

- **`write_output()`**: Writes the snapshot dictionary to a file in either `json` or `jsonl` format.

- **`token_estimate()`**: A simple utility function to estimate the token count of a string using a 4-character heuristic.

- **`is_text_file()`**: A helper that determines if a file should be treated as text based on its extension, size, and content (by checking for null bytes).

### Example

```python
import paleae
from pathlib import Path

def create_custom_snapshot():
    root = Path(".")
    
    # 1. Define patterns (see Configuration guide)
    inc_patterns = paleae.compile_patterns([r"\.py$", r"\.md$"])
    exc_patterns = paleae.compile_patterns([r"test_", r"__pycache__"])
    
    # 2. Collect files
    # The last two arguments are for .paleaeignore patterns
    files = paleae.collect_files(root, inc_patterns, exc_patterns, [], [])
    
    # 3. Build snapshot (see Output Format guide)
    snapshot = paleae.build_snapshot(root, files, {})
    
    # 4. Write output
    paleae.write_output(Path("custom_snapshot.json"), snapshot, "json")
    
    print(f"Successfully created snapshot with {len(files)} files.")

if __name__ == "__main__":
    create_custom_snapshot()
```

For more complex examples, such as integrating with Git or creating custom reports, see the [Advanced Usage](Advanced-Usage) guide.

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
