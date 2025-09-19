#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Paul Tiffany
# Project: paleae - Snapshot your repo for LLMs
# Website: https://paleae.com
# Source:  https://github.com/PaulTiffany/paleae

"""
paleae - Create JSON/JSONL snapshots of your repository for LLMs.

A single-file, zero-dependency tool that scans your codebase and creates
structured snapshots optimized for AI analysis and processing.
"""

import argparse
import fnmatch
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Optional

# Project metadata (also embedded in output)
__version__ = "1.0.0"
__license__ = "MIT"
__website__ = "https://paleae.com"
__source__ = "https://github.com/PaulTiffany/paleae"

# --- Configuration ---
MAX_SIZE = 10 * 1024 * 1024  # 10MB
PALEAEIGNORE = ".paleaeignore"

TEXT_EXTS = {
    ".py",
    ".md",
    ".rst",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".xml",
    ".csv",
    ".tsv",
    ".html",
    ".css",
    ".js",
    ".ts",
    ".tsx",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".sh",
    ".ps1",
}

DEFAULT_SKIP = [
    r"(^|/)\.(git|hg|svn)($|/)",
    r"(^|/)__pycache__($|/)",
    r"(^|/)\.(pytest|mypy|ruff)_cache($|/)",
    r"(^|/)(\.?venv|env)($|/)",
    r"(^|/)node_modules($|/)",
    r"(^|/)(build|dist)($|/)",
    r"(^|/)coverage($|/)",
    r"(^|/)htmlcov($|/)",
    r"(^|/)\.coverage($|/)?",
    r"(^|/)\.env($|/)",
    r"(^|/)" + re.escape(PALEAEIGNORE) + r"($|/)?",  # Ignore our own config file
]

PROFILES = {
    "minimal": {"include": [r".*"], "exclude": DEFAULT_SKIP},
    "ai_optimized": {
        "include": [
            r"^(src|tests)(/.*)?$",
            r"^pyproject\.toml$",
            r"^README(\.md|\.rst)?$",
            r"^(ROADMAP|CHANGELOG)\.md$",
        ],
        "exclude": DEFAULT_SKIP + [r"(^|/)docs/"],
    },
}

# --- Core Logic ---


class PaleaeError(Exception):
    """Base exception for paleae operations."""


def token_estimate(text: str) -> int:
    """Estimate tokens using 4-char heuristic."""
    return max(1, len(text) // 4) if text else 0


def is_text_file(path: Path) -> bool:
    """Check if file should be treated as text."""
    if not path.is_file():
        return False
    try:
        size = path.stat().st_size
        if size == 0:
            return path.suffix.lower() in TEXT_EXTS or path.suffix == ""
        if size > MAX_SIZE:
            return False
        with path.open("rb") as f:
            chunk = f.read(min(1024, size))
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError, PermissionError):
        return False


def _translate_globs_to_regex(globs: list[str]) -> list[str]:
    """Translate shell globs to regex strings with normalization."""
    regex_list: list[str] = []
    for glob_pattern in globs:
        line = glob_pattern.strip()
        if not line or line.startswith("#"):
            continue
        # fnmatch.translate handles **, *, ?, and char classes
        regex_list.append(fnmatch.translate(line))
    return regex_list


def read_paleaeignore(root: Path) -> tuple[list[str], list[str]]:
    """Return (positive_globs, negative_globs) from .paleaeignore."""
    pos: list[str] = []
    neg: list[str] = []
    path = root / PALEAEIGNORE
    if not path.is_file():
        return pos, neg
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line_item in lines:
            line = line_item.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("!"):
                neg.append(line[1:].strip())
            else:
                pos.append(line)
    except (OSError, PermissionError):
        print(f"Warning: Could not read {PALEAEIGNORE}", file=sys.stderr)
    return pos, neg


def compile_patterns(patterns: Optional[list[str]]) -> list[re.Pattern[str]]:
    """Compile regex patterns with error handling."""
    if not patterns:
        return []
    compiled = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern))
        except re.error as e:
            raise PaleaeError(f"Invalid regex '{pattern}': {e}") from e
    return compiled


def matches_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    """Check if text matches any pattern."""
    return any(p.search(text) for p in patterns)


def collect_files(
    root: Path,
    inc_patterns: list[re.Pattern[str]],
    exc_patterns: list[re.Pattern[str]],
    ign_pos_patterns: list[re.Pattern[str]],
    ign_neg_patterns: list[re.Pattern[str]],
) -> list[str]:
    """Collect files matching all filter criteria."""
    if not root.is_dir():
        raise PaleaeError(f"Directory not found: {root}")

    files = []
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            try:
                rel_path = path.relative_to(root).as_posix()
            except ValueError:
                continue

            # Step 1: Check if the path is excluded by default, CLI, or .paleaeignore
            is_excluded = matches_any(rel_path, exc_patterns) or matches_any(
                rel_path, ign_pos_patterns
            )

            # Step 2: A negative pattern (!) in .paleaeignore overrides any exclusion
            if is_excluded and matches_any(rel_path, ign_neg_patterns):
                is_excluded = False

            if is_excluded:
                continue

            # Step 3: Check if the path meets the inclusion criteria
            if inc_patterns and not matches_any(rel_path, inc_patterns):
                continue

            if is_text_file(path):
                files.append(rel_path)
    except (OSError, PermissionError) as e:
        raise PaleaeError(f"Error traversing {root}: {e}") from e
    return sorted(files)


def build_snapshot(root: Path, rel_files: list[str], ignore_meta: dict[str, Any]) -> dict[str, Any]:
    """Build complete snapshot data, including metadata."""
    files_data, total_chars, total_tokens = [], 0, 0
    for rel_path in rel_files:
        full_path = root / rel_path
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            if not content.strip():
                continue
        except (OSError, PermissionError, UnicodeDecodeError):
            continue

        chars = len(content)
        tokens = token_estimate(content)
        files_data.append(
            {
                "path": rel_path,
                "content": content,
                "size_chars": chars,
                "sha256": hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest(),
                "estimated_tokens": tokens,
            }
        )
        total_chars += chars
        total_tokens += tokens

    return {
        "meta": {
            "tool": "paleae",
            "version": __version__,
            "license": __license__,
            "website": __website__,
            "source": __source__,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "root_directory": str(root),
            "ignore_file": ignore_meta,
            "summary": {
                "total_files": len(files_data),
                "total_chars": total_chars,
                "estimated_tokens": total_tokens,
            },
        },
        "files": files_data,
    }


def write_output(path: Path, data: dict[str, Any], format: str) -> None:
    """Write data as JSON or JSONL file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if format == "json":
            content = json.dumps(data, indent=2, ensure_ascii=False)
            path.write_text(content, encoding="utf-8")
        else:  # jsonl
            with path.open("w", encoding="utf-8") as f:
                f.write(json.dumps({"type": "meta", **data["meta"]}, ensure_ascii=False) + "\n")
                for row in data["files"]:
                    f.write(json.dumps({"type": "file", **row}, ensure_ascii=False) + "\n")
    except (OSError, PermissionError) as e:
        raise PaleaeError(f"Error writing {path}: {e}") from e


# --- CLI and Main Execution ---


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(description="Create JSON/JSONL snapshot of your repo for LLMs")
    parser.add_argument(
        "directory", nargs="?", default=".", help="Directory to snapshot (default: .)"
    )
    parser.add_argument("-o", "--out", help="Output file (auto-named if not specified)")
    parser.add_argument(
        "-f", "--format", choices=["json", "jsonl"], default="json", help="Output format"
    )
    parser.add_argument(
        "--profile", choices=list(PROFILES.keys()), default="minimal", help="File inclusion profile"
    )
    parser.add_argument("--include", action="append", help="Extra include regex (repeatable)")
    parser.add_argument("--exclude", action="append", help="Extra exclude regex (repeatable)")
    parser.add_argument("--version", action="version", version=f"paleae {__version__}")
    parser.add_argument("--about", action="store_true", help="Show project info and exit")
    return parser


def main() -> int:  # noqa: PLR0911
    """Run the main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if args.about:
        print(
            f"paleae {__version__} ({__license__})\nWebsite: {__website__}\nSource:  {__source__}"
        )
        return 0

    try:
        # --- Setup ---
        root = Path(args.directory).resolve()
        if not root.is_dir():
            print(f"Error: '{args.directory}' is not a directory", file=sys.stderr)
            return 1

        # --- Pattern Compilation ---
        profile = PROFILES.get(args.profile, PROFILES["minimal"])
        inc_cli = compile_patterns((args.include or []) + profile["include"])
        exc_cli = compile_patterns((args.exclude or []) + profile["exclude"])

        pos_globs, neg_globs = read_paleaeignore(root)
        ign_pos_rx = compile_patterns(_translate_globs_to_regex(pos_globs))
        ign_neg_rx = compile_patterns(_translate_globs_to_regex(neg_globs))
        ignore_meta = {
            "file": PALEAEIGNORE,
            "present": bool(pos_globs or neg_globs),
            "patterns": len(pos_globs),
            "negations": len(neg_globs),
        }

        # --- File Collection ---
        files = collect_files(root, inc_cli, exc_cli, ign_pos_rx, ign_neg_rx)
        if not files:
            print("No text files found matching criteria.", file=sys.stderr)
            return 1

        # --- Snapshot Generation & Output ---
        data = build_snapshot(root, files, ignore_meta)
        out_path = Path(args.out) if args.out else Path(f"repo_snapshot.{args.format}")
        write_output(out_path, data, args.format)

        # --- Summary ---
        s = data["meta"]["summary"]
        print(f"✓ Snapshot saved to {out_path}")
        print(
            f"  Files: {s['total_files']}  "
            f"Characters: {s['total_chars']:,}  "
            f"Tokens: {s['estimated_tokens']:,}"
        )
        return 0

    except PaleaeError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def cli_entrypoint() -> None:
    """Console entry point (kept tiny so tests can patch sys.exit)."""
    sys.exit(main())


if __name__ == "__main__":
    cli_entrypoint()
