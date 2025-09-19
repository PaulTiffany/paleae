
#!/usr/bin/env python3
"""
paleae_lite — Snapshot your repo for LLMs (v1.0.0-lite)

One-file tool to create JSON or JSONL snapshots of your codebase.

Usage:
    python paleae_lite.py                   # snapshot current directory -> repo_snapshot.json
    python paleae_lite.py . --format jsonl  # row-wise feed -> repo_feed.jsonl
    python paleae_lite.py path --out out.json --include '^(src|tests)/' --exclude '\\.git/'

This is intentionally small and dependency-free.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Pattern

VERSION = "1.0.0-lite"

# --- Defaults ---------------------------------------------------------------

TEXT_EXTENSIONS = {
    ".py",".pyi",".md",".rst",".txt",".json",".yaml",".yml",".toml",".ini",".cfg",
    ".xml",".csv",".tsv",".html",".css",".js",".ts",".tsx",".c",".h",".cpp",".hpp",
    ".java",".kt",".go",".rs",".rb",".php",".sh",".ps1"
}

DEFAULT_SKIP = [
    r"(^|/)\\.git($|/)", r"(^|/)\\.hg($|/)", r"(^|/)\\.svn($|/)",
    r"(^|/)__pycache__($|/)", r"(^|/)\\.pytest_cache($|/)",
    r"(^|/)\\.mypy_cache($|/)", r"(^|/)\\.ruff_cache($|/)",
    r"(^|/)\\.venv($|/)", r"(^|/)venv($|/)", r"(^|/)env($|/)",
    r"(^|/)node_modules($|/)", r"(^|/)build($|/)", r"(^|/)dist($|/)",
    r"(^|/)coverage($|/)", r"(^|/)htmlcov($|/)",
    r"(^|/)\\.coverage($|/)?", r"(^|/)\\.env($|/)"
]

PROFILES = {
    "minimal": {"include": [r".*"], "exclude": DEFAULT_SKIP},
    "ai_optimized": {
        "include": [
            r"^(src|pylantern|tests)(/.*)?$",
            r"^pyproject\\.toml$", r"^README(\\.md|\\.rst)?$",
            r"^ROADMAP\\.md$", r"^CHANGELOG\\.md$",
            r"^reports/(pytest_results\\.xml|coverage\\.xml)$",
        ],
        "exclude": DEFAULT_SKIP + [r"(^|/)docs/"]
    },
}

# --- Helpers ----------------------------------------------------------------

def estimate_tokens(text: str) -> int:
    # Rough: ~4 chars per token
    return max(1, len(text) // 4)

def is_text_file(path: str) -> bool:
    ext = os.path.splitext(path)[1].lower()
    if ext in TEXT_EXTENSIONS:
        return True
    try:
        with open(path, "rb") as f:
            chunk = f.read(1024)
        if b"\\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except Exception:
        return False

def compile_patterns(patterns: List[str]) -> List[Pattern]:
    return [re.compile(p) for p in (patterns or [])]

def matches_any(text: str, patterns: List[Pattern]) -> bool:
    return any(p.search(text) for p in patterns)

def normalize_rel(rel: str) -> str:
    rel = rel.replace("\\\\", "/")
    return "." if rel == "." else rel

# --- Core -------------------------------------------------------------------

def collect_files(root: str, inc: List[Pattern], exc: List[Pattern]) -> List[str]:
    root = os.path.abspath(root)
    rels: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = normalize_rel(os.path.relpath(dirpath, root))
        rel_dir = "" if rel_dir == "." else rel_dir
        # directory-level exclude quick check
        if rel_dir and matches_any(rel_dir + "/", exc):
            dirnames[:] = []  # prune
            continue
        # filter child dirs
        dirnames[:] = [d for d in dirnames if not matches_any(os.path.join(rel_dir, d).replace("\\\\", "/") + "/", exc)]
        # files
        for fn in sorted(filenames):
            rel = (os.path.join(rel_dir, fn) if rel_dir else fn).replace("\\\\", "/")
            full = os.path.join(root, rel)
            if matches_any(rel, exc):
                continue
            if inc and not matches_any(rel, inc):
                continue
            if os.path.isfile(full) and is_text_file(full):
                rels.append(rel)
    rels.sort()
    return rels

def read_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""

def build_snapshot(root: str, files: List[str]) -> Dict[str, Any]:
    root_abs = os.path.abspath(root)
    out_files: List[Dict[str, Any]] = []
    total_chars = 0
    total_tokens = 0

    for rel in files:
        full = os.path.join(root_abs, rel)
        text = read_text(full)
        if not text:
            continue
        size_chars = len(text)
        tokens = estimate_tokens(text)
        out_files.append({
            "path": rel,
            "content": text,
            "size_chars": size_chars,
            "sha256": hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest(),
            "estimated_tokens": tokens,
        })
        total_chars += size_chars
        total_tokens += tokens

    meta = {
        "tool": "paleae-lite",
        "version": VERSION,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root_directory": root_abs,
        "summary": {
            "total_files": len(out_files),
            "total_chars": total_chars,
            "estimated_tokens": total_tokens,
        },
    }
    return {"meta": meta, "files": out_files}

def write_json(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def write_jsonl(path: str, data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    meta = data.get("meta", {})
    files = data.get("files", [])
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"type": "meta", **meta}, ensure_ascii=False) + "\\n")
        for row in files:
            f.write(json.dumps({"type": "file", **row}, ensure_ascii=False) + "\\n")

# --- CLI --------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Create a JSON or JSONL snapshot of your repository for LLMs",
        epilog="Example: python paleae_lite.py . --format jsonl --out repo_feed.jsonl"
    )
    p.add_argument("directory", nargs="?", default=".", help="Directory to snapshot (default: .)")
    p.add_argument("--out", "-o", default=None, help="Output file path (default by format)")
    p.add_argument("--format", "-f", default="json", choices=["json", "jsonl"], help="Output format")
    p.add_argument("--profile", default="minimal", choices=list(PROFILES.keys()), help="Inclusion profile")
    p.add_argument("--include", action="append", default=None, help="Additional include regex (repeatable)")
    p.add_argument("--exclude", action="append", default=None, help="Additional exclude regex (repeatable)")
    p.add_argument("--version", action="version", version=f"paleae-lite {VERSION}")
    args = p.parse_args(argv)

    # Compile filters
    prof = PROFILES.get(args.profile, PROFILES["minimal"])
    inc = compile_patterns((args.include or []) + prof["include"])
    exc = compile_patterns((args.exclude or []) + prof["exclude"])

    # Validate directory
    if not os.path.isdir(args.directory):
        print(f"Error: '{args.directory}' is not a directory", file=sys.stderr)
        return 1

    # Collect + snapshot
    files = collect_files(args.directory, inc, exc)
    data = build_snapshot(args.directory, files)

    # Write
    default_out = "repo_snapshot.json" if args.format == "json" else "repo_feed.jsonl"
    out_path = args.out or default_out
    if args.format == "json":
        write_json(out_path, data)
    else:
        write_jsonl(out_path, data)

    # Summary to stdout
    meta = data["meta"]["summary"]
    print(f"✓ Snapshot saved to {out_path}")
    print(f"  Files: {meta['total_files']}")
    print(f"  Characters: {meta['total_chars']:,}")
    print(f"  Estimated tokens: {meta['estimated_tokens']:,}")
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
