<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/paleae-badge-dark.svg">
    <img alt="Paleae — Ship your repo to your AI" src="./assets/paleae-badge-light.svg" width="230">
  </picture>
</p>

<p align="center">
  <strong>Snapshot your codebase into compact JSON/JSONL — perfect for LLMs.</strong>
  <br>
  Single file. Zero dependencies. No install.
</p>

<p align="center">
  <!-- TODO: Update username/repo in the CI badge URL -->
  <a href="https://github.com/PaulTiffany/paleae/actions/workflows/ci.yml">
    <img src="https://github.com/PaulTiffany/paleae/actions/workflows/ci.yml/badge.svg" alt="CI Status">
  </a>
  <a href="https://pypi.org/project/paleae/">
    <img src="https://img.shields.io/pypi/v/paleae.svg?color=5EE1A0&label=pypi%20package" alt="PyPI version">
  </a>
  <a href="https://pypi.org/project/paleae/">
    <img src="https://img.shields.io/pypi/pyversions/paleae.svg" alt="Python versions">
  </a>
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-informational.svg" alt="MIT License">
  </a>
</p>

---

`paleae` is a single-file, zero-dependency utility that scans your repository and creates a structured snapshot optimized for AI analysis. It's designed to be simple, transparent, and trustworthy.

## Key Features

*   **Single File, Zero Deps:** Drop `paleae.py` into any project. It runs anywhere Python runs, with no `pip install` required.
*   **Local-First:** Scans files on your machine. No code is ever sent over the network.
*   **Structured Output:** Generates clean `JSON` or `JSONL`, including file paths, content, and SHA-256 hashes.
*   **Configurable:** Use powerful include/exclude regex patterns and a `.paleaeignore` file (with `!` negation) to precisely control what gets included.
*   **Rigorously Tested:** 100% line and branch coverage, fully type-checked with MyPy, linted with Ruff, and hardened with Hypothesis property-based tests and `pydocstyle` compliance.

## Quick Start

No installation needed. Just download and run.

```bash
# Download the script
curl -fsSL https://raw.githubusercontent.com/PaulTiffany/paleae/main/paleae.py -o paleae.py

# Snapshot the current directory
python paleae.py
```

This will create a `repo_snapshot.json` file in your current directory.

## Usage

```
usage: paleae [-h] [-o OUT] [-f {json,jsonl}] [--profile {minimal,ai_optimized}]
              [--include INCLUDE] [--exclude EXCLUDE] [--version] [--about]
              [directory]

Create JSON/JSONL snapshot of your repo for LLMs

positional arguments:
  directory             Directory to snapshot (default: .)

options:
  -h, --help            show this help message and exit
  -o, --out OUT         Output file (auto-named if not specified)
  -f, --format {json,jsonl}
                        Output format
  --profile {minimal,ai_optimized}
                        File inclusion profile
  --include INCLUDE     Extra include regex (repeatable)
  --exclude EXCLUDE     Extra exclude regex (repeatable)
  --version             show program's version number and exit
  --about               Show project info and exit
```

### Examples

**Snapshot to a specific JSONL file:**
```bash
python paleae.py -f jsonl -o my_project.jsonl
```

**Use the `ai_optimized` profile to include only core source and config files:**
```bash
python paleae.py --profile ai_optimized
```

**Add a specific directory to the snapshot using a regex:**
```bash
python paleae.py --include "^(docs|examples)/"
```

## Configuration (`.paleaeignore`)

Create a `.paleaeignore` file in your project's root directory to exclude files and directories. The syntax is similar to `.gitignore`.

```
# .paleaeignore

# Ignore build artifacts and logs
build/
dist/
*.log

# But force-include an important log file
!important.log
```

## Output Format

The snapshot contains metadata and a list of file objects.

```json
{
  "meta": {
    "tool": "paleae",
    "version": "1.2.0",
    "timestamp": "2025-09-16T20:00:00Z",
    "root_directory": "/path/to/your/project",
    "summary": {
      "total_files": 42,
      "total_chars": 123456,
      "estimated_tokens": 30864
    }
  },
  "files": [
    {
      "path": "src/main.py",
      "content": "print('hello')",
      "size_chars": 14,
      "sha256": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
      "estimated_tokens": 3
    }
  ]
}
```

## License

This project is licensed under the [MIT License](./LICENSE).

The brand assets (`assets/*.svg`) are dedicated to the public domain under [CC0 1.0 Universal](./assets/LICENSE.txt).
