#!/usr/bin/env python3
"""
PalaePro Directory Snapshot Tool for AI Coding Assistants (v3.0.2)

A powerful tool to create structured, context-rich snapshots of directory
trees optimized for AI coding assistants.
"""

import argparse
import ast
import configparser
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import time
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Try to import tiktoken for better token counting
try:
    import tiktoken  # type: ignore[import-not-found]

    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

# Initialize mimetypes
mimetypes.init()

# --- Data Classes for Structured Output ---


@dataclass
class CodeStructure:
    """Structured analysis of a source code file."""

    imports: List[str] = field(default_factory=list)
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FileMetadata:
    """Metadata for a file entry."""

    name: str
    type: str
    path: str
    size: int
    modified_time: str
    is_key_file: bool = False
    purpose: Optional[str] = None  # Added for AI context
    encoding: Optional[str] = None
    mime_type: Optional[str] = None
    hash_sha256: Optional[str] = None
    lines: Optional[int] = None
    tokens_estimate: Optional[int] = None
    is_binary: bool = False
    content: Optional[str] = None
    structure: Optional[CodeStructure] = None
    error: Optional[str] = None


@dataclass
class DirectoryStats:
    """Statistics for the directory snapshot."""

    total_files: int = 0
    total_directories: int = 0
    total_size: int = 0
    text_files: int = 0
    binary_files: int = 0
    symlinks: int = 0
    errors: int = 0
    estimated_tokens: int = 0


@dataclass
class GitInfo:
    """Information about the Git repository state."""

    branch: Optional[str] = None
    recent_commits: List[str] = field(default_factory=list)
    status: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SnapshotMetadata:
    """Complete metadata about the snapshot."""

    generated_at: str
    root_path: str
    tool_version: str = "3.0.2"
    config: Optional[Dict] = None
    filters: Optional[Dict] = None
    format_version: str = "3.0"


@dataclass
class Snapshot:
    """Complete snapshot structure."""

    metadata: SnapshotMetadata
    statistics: DirectoryStats
    tree: Dict
    git_info: Optional[GitInfo] = None
    dependencies: Optional[Dict[str, List[str]]] = field(default_factory=dict)
    key_files: List[str] = field(default_factory=list)


# --- Core Logic Classes ---


class ProgressTracker:
    """Thread-safe progress tracker for large operations."""

    def __init__(self, total: int, description: str = "Processing"):
        self.total = total
        self.current = 0
        self.description = description
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.last_update = 0

    def update(self, increment: int = 1):
        with self.lock:
            self.current += increment
            now = time.time()
            if now - self.last_update > 0.1 or self.current >= self.total:
                self.last_update = now
                elapsed = now - self.start_time
                if self.current > 0 and self.total > 0:
                    eta = (elapsed / self.current) * (self.total - self.current)
                    percentage = (self.current / self.total) * 100
                    print(
                        f"{self.description}: {self.current}/{self.total} "
                        f"({percentage:.1f}%) - ETA: {eta:.1f}s",
                        end="\r",
                        flush=True,
                    )

    def complete(self):
        elapsed = time.time() - self.start_time
        print(
            f"{self.description}: {self.current}/{self.total} (100%) - "
            f"Completed in {elapsed:.1f}s"
        )


class TokenEstimator:
    """Advanced token estimation for AI context planning and profile-aware
    estimation."""

    def __init__(self):
        self.encoder = None
        if HAS_TIKTOKEN:
            try:
                self.encoder = tiktoken.encoding_for_model("gpt-4")
            except Exception:
                try:
                    self.encoder = tiktoken.get_encoding("cl100k_base")
                except Exception:
                    self.encoder = None

    def estimate_tokens(self, content: str) -> int:
        if not content:
            return 0
        if self.encoder:
            try:
                return len(self.encoder.encode(content))
            except Exception:
                return len(content) // 4
        return len(content) // 4

    @staticmethod
    def estimate_profile_impact(root_path: str, profiles: Optional[List[str]] = None):
        """Quick file count and size estimate per exclusion profile."""
        profiles = profiles or list(PalaePro.EXCLUSION_PROFILES.keys())
        print(f"Estimating impact of exclusion profiles under: {root_path}\n")

        for profile in profiles:
            snap = PalaePro(profile=profile)
            count, total_size, py_files = 0, 0, 0

            for dirpath, dirnames, filenames in os.walk(root_path):
                # Apply directory exclusions
                dirnames[:] = [d for d in dirnames if d not in snap.exclude_dirs]

                for file in filenames:
                    if any(file.endswith(ext) for ext in snap.exclude_files):
                        continue
                    try:
                        fpath = os.path.join(dirpath, file)
                        total_size += os.path.getsize(fpath)
                        count += 1
                        if file.endswith(".py"):
                            py_files += 1
                    except Exception:
                        continue

            size_kb = total_size / 1024
            print(
                f"Profile `{profile}` -> ~{count} files ({py_files} .py), "
                f"{size_kb:.1f} KB"
            )

        print(
            "\nUse --profile <name> to select exclusion level for snapshot "
            "generation."
        )


class CodeParser(ast.NodeVisitor):
    """AST visitor to extract code structure from Python source."""

    def __init__(self, source_code: str):
        self.structure = CodeStructure()
        self.source_code = source_code

    def visit_Import(self, node):
        for alias in node.names:
            self.structure.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        module_name = node.module or "." * node.level
        for alias in node.names:
            self.structure.imports.append(f"{module_name}.{alias.name}")
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        try:
            args_source = ast.get_source_segment(self.source_code, node.args)
            signature = f"def {node.name}{args_source}:"
        except Exception:
            signature = f"def {node.name}(...):"
        self.structure.functions.append(
            {
                "name": node.name,
                "signature": signature,
                "docstring": ast.get_docstring(node),
            }
        )
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
        self.structure.classes.append(
            {
                "name": node.name,
                "methods": methods,
                "docstring": ast.get_docstring(node),
            }
        )
        # Do not visit children of classes to avoid listing methods as
        # top-level functions.
        # self.generic_visit(node) # This would be needed for nested classes.


class PalaePro:
    """The main class for generating directory snapshots."""

    EXCLUSION_PROFILES = {
        "minimal": {
            "dirs": [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "env",
                ".env",
                "dist",
                "build",
            ],
            "files": [
                ".pyc",
                ".pyo",
                ".pyd",
                ".so",
                ".egg-info",
                ".DS_Store",
                "Thumbs.db",
            ],
        },
        "ai_optimized": {
            "dirs": [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "env",
                ".env",
                "dist",
                "build",
                "coverage",
                ".pytest_cache",
                ".mypy_cache",
                "logs",
                "log",
                "tmp",
                "temp",
                "site",
                ".idea",
                ".vscode",
            ],
            "files": [
                ".pyc",
                ".pyo",
                ".pyd",
                ".so",
                ".egg-info",
                ".DS_Store",
                "Thumbs.db",
            ],
        },
        "gemini_optimized": {
            "dirs": [
                ".git",
                "__pycache__",
                "node_modules",
                ".venv",
                "venv",
                "env",
                ".env",
                "dist",
                "build",
                "coverage",
                ".pytest_cache",
                ".mypy_cache",
                "logs",
                "log",
                "tmp",
                "temp",
                "site",
                ".idea",
                ".vscode",
                "SRV",
                "artifacts",
                "docs",
                "examples",
                "pylantern.egg-info",
            ],
            "files": [
                ".pyc",
                ".pyo",
                ".pyd",
                ".so",
                ".egg-info",
                ".DS_Store",
                "Thumbs.db",
                "temp_*.json",
                "temp_*.txt",
            ],
        },
    }

    KEY_FILE_PATTERNS = [
        re.compile(p, re.IGNORECASE)
        for p in [
            r"^README(\.md|\.rst|\.txt)?$",
            r"^(docker-compose|dockerfile).*$",
            r"^requirements.*\.txt$",
            r"^package.json$",
            r"^pyproject.toml$",
            r"^pom.xml$",
            r"^build.gradle$",
            r"^\.env(\.example)?$",
            r"^\.gitignore$",
            r"^\.dockerignore$",
            r"^\.github[\\/]workflows[\\/].*\.ya?ml$",
        ]
    ]

    MODEL_TOKEN_LIMITS = {
        "flash": 128000,  # Example limit for a large context window model like Flash
        "pro": 256000,  # Example limit for an even larger context window model like Pro
        "default": 8000,  # Original default
    }

    def __init__(
        self,
        config_file: Optional[str] = None,
        profile: str = "minimal",
        model_profile: str = "default",
    ):
        self.config = self._load_config(config_file)
        self.profile = profile
        self.stats = DirectoryStats()
        self.token_estimator = TokenEstimator()
        self.progress = None
        self.key_files = []
        self.all_file_paths = set()
        self.module_to_path_map = {}

        profile_data = self.EXCLUSION_PROFILES.get(
            profile, self.EXCLUSION_PROFILES["minimal"]
        )
        self.exclude_dirs = set(profile_data["dirs"])
        self.exclude_files = set(profile_data["files"])

        # Set max_tokens_per_file based on model_profile, if not overridden by
        # config file
        if (
            model_profile in self.MODEL_TOKEN_LIMITS
            and "max_tokens_per_file" not in self.config
        ):
            self.config["max_tokens_per_file"] = self.MODEL_TOKEN_LIMITS[model_profile]

    def _load_config(self, config_file: Optional[str]) -> Dict:
        """Load configuration from file with environment variable support."""
        default_config = {
            "max_file_size": 1 * 1024 * 1024,  # 1MB
            "max_depth": 20,
            "max_tokens_per_file": 8000,
            "show_progress": True,
            "include_hash": False,
            "follow_symlinks": False,
            "use_git": True,
            "use_ast": True,
            "use_deps": True,
            "summarize_lines": 25,
        }

        if not config_file:
            # Look for default config files
            for default_name in [".paleaepro.ini", "paleaepro.ini", ".paleaepro.conf"]:
                if os.path.exists(default_name):
                    config_file = default_name
                    break

        if config_file and os.path.exists(config_file):
            try:
                config = configparser.ConfigParser()
                config.read(config_file)

                if "paleaepro" in config:
                    section = config["paleaepro"]
                    for key in default_config:
                        if key in section:
                            # Type conversion
                            if isinstance(default_config[key], bool):
                                default_config[key] = section.getboolean(key)
                            elif isinstance(default_config[key], int):
                                default_config[key] = section.getint(key)
                            else:
                                default_config[key] = section[key]
            except Exception as e:
                print(
                    f"Warning: Could not load config file {config_file}: {e}",
                    file=sys.stderr,
                )

        return default_config

    def _run_command(self, command: List[str], cwd: str) -> Optional[str]:
        """Helper to run a shell command and capture output."""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
                encoding="utf-8",
                errors="ignore",
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (FileNotFoundError, subprocess.SubprocessError):
            return None
        return None

    def _get_git_info(self, root_path: str) -> Optional[GitInfo]:
        """Gather information from the git repository."""
        if not self.config.get("use_git"):
            return None

        git_dir = self._run_command(["git", "rev-parse", "--git-dir"], root_path)
        if not git_dir:
            return GitInfo(error="Not a git repository or git command not found.")

        repo_root = (
            self._run_command(["git", "rev-parse", "--show-toplevel"], root_path)
            or root_path
        )

        info = GitInfo()
        info.branch = self._run_command(["git", "branch", "--show-current"], repo_root)
        info.status = self._run_command(["git", "status", "--porcelain"], repo_root)
        commits_str = self._run_command(
            ["git", "log", "-n", "5", "--pretty=format:%h - %s (%cr)"], repo_root
        )
        if commits_str:
            info.recent_commits = commits_str.split("\n")
        return info

    def _is_key_file(self, relative_path: str) -> bool:
        """Check if a file is a 'key' project file."""
        # Normalize path separators for regex matching
        normalized_path = relative_path.replace(os.sep, "/")
        for pattern in self.KEY_FILE_PATTERNS:
            if pattern.match(normalized_path):
                return True
        return False

    def _analyze_code_structure(
        self,
        file_path: str,
        content: str,
    ) -> Optional[CodeStructure]:
        """Parse a file to extract its structure using AST."""
        if not self.config.get("use_ast") or not file_path.endswith(".py"):
            return None
        try:
            tree = ast.parse(content, filename=file_path)
            visitor = CodeParser(source_code=content)
            visitor.visit(tree)
            return visitor.structure
        except SyntaxError:
            return None  # Can't parse, not valid Python

    def _summarize_large_file(
        self,
        content: str,
        structure: Optional[CodeStructure],
    ) -> str:
        """Create a summary for a file that exceeds the token limit,
        prioritizing key code elements."""
        summary_parts = ["[File content too large, providing intelligent summary.]\n"]

        if structure:
            if structure.imports:
                summary_parts.append(
                    "Imports:\n  " + "\n  ".join(sorted(set(structure.imports)))
                )

            if structure.classes:
                summary_parts.append("\nClasses:")
                for cls in structure.classes:
                    summary_parts.append(
                        f"  - class {cls['name']}(\n" 
                                                f"      Methods: {', '.join(cls['methods']) if cls['methods'] else 'None'}"
                        f"\n"  # noqa: E501
                        f"      Docstring: {cls['docstring'] or 'None'}\n"
                        f"    )"
                    )

            if structure.functions:
                summary_parts.append("\nFunctions:")
                for func in structure.functions:
                    summary_parts.append(
                        f"  - {func['signature']}\n"
                        f"      Docstring: {func['docstring'] or 'None'}"
                    )
        main_block_match = re.search(
            r"^if __name__ == [\"']__main[\"']:", content, re.MULTILINE
        )
        if main_block_match:
            summary_parts.append('\nMain Execution Block (if __name__ == "__main__"):')
            summary_parts.append("  [...main execution block found...]")

        # Fallback to line-based summary if AST didn't provide much or for
        # non-Python files
        if (
            len("\n".join(summary_parts)) < 200
        ):  # Arbitrary threshold to decide if AST summary is too short
            lines = content.splitlines()
            num_lines = self.config.get("summarize_lines", 25)
            if len(lines) > num_lines * 2:
                summary_parts.append("\n--- Start of File (truncated) ---")
                summary_parts.extend(lines[:num_lines])
                summary_parts.append("...")
                summary_parts.append("--- End of File (truncated) ---")
                summary_parts.extend(lines[-num_lines:])
            else:
                summary_parts.append("\n--- Full File Content ---")
                summary_parts.extend(lines)

        final_summary = "\n".join(summary_parts)
        # Ensure summary doesn't exceed token limit
        estimated_tokens = self.token_estimator.estimate_tokens(final_summary)
        if estimated_tokens > self.config["max_tokens_per_file"]:
            # Trim aggressively if still too large
            while (
                estimated_tokens > self.config["max_tokens_per_file"] * 0.9
                and len(final_summary) > 100
            ):
                final_summary = final_summary[: len(final_summary) // 2]
                estimated_tokens = self.token_estimator.estimate_tokens(final_summary)
            final_summary += "\n[Summary truncated due to token limit]"

        return final_summary

    def _determine_file_purpose(self, relative_path: str) -> Optional[str]:
        """Determine the likely purpose of a file based on its path and name."""
        path_lower = relative_path.lower().replace(os.sep, "/")
        file_name_lower = os.path.basename(path_lower)

        if self._is_key_file(relative_path):
            return "config_or_meta"
        if "test" in path_lower or file_name_lower.startswith("test_"):
            return "test"
        if "doc" in path_lower or file_name_lower.startswith("readme"):
            return "documentation"
        if file_name_lower.endswith(
            (".py", ".js", ".ts", ".java", ".go", ".c", ".cpp", ".h")
        ):
            return "source_code"
        if file_name_lower.endswith((".json", ".xml", ".yaml", ".yml", ".ini", ".env")):
            return "configuration"
        if file_name_lower.endswith((".csv", ".tsv", ".xlsx", ".hdf5")):
            return "data"
        if file_name_lower.endswith((".md", ".rst")):
            return "documentation"

        return None

    def _process_file(self, file_path: str, relative_path: str) -> FileMetadata:
        """Process a single file, including content, tokens, and structure."""
        try:
            stat_info = os.stat(file_path)
            file_size = stat_info.st_size
            is_key = self._is_key_file(relative_path)
            if is_key:
                self.key_files.append(relative_path)

            file_meta = FileMetadata(
                name=os.path.basename(file_path),
                type="file",
                path=relative_path,
                size=file_size,
                modified_time=datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                is_key_file=is_key,
                purpose=self._determine_file_purpose(relative_path),  # Assign purpose
            )

            # Determine if file is binary or too large
            is_binary = False
            if file_size > self.config["max_file_size"]:
                is_binary = True
                file_meta.error = "file_size_exceeded"
            else:
                mime_type, _ = mimetypes.guess_type(file_path)
                file_meta.mime_type = mime_type
                if (
                    mime_type
                    and not mime_type.startswith("text/")
                    and not mime_type.startswith("inode/directory")
                ):
                    is_binary = True
                else:
                    # Check for null byte in the first 8KB for text files
                    try:
                        with open(file_path, "rb") as f:
                            if b"\x00" in f.read(8192):
                                is_binary = True
                    except OSError:
                        # If an OSError occurs during the null-byte check, treat
                        # as binary
                        is_binary = True
                        self.stats.errors += (
                            1  # Increment error count for unreadable files
                        )

            file_meta.is_binary = is_binary
            if is_binary:
                file_meta.content = "[Binary file content not included]"
                self.stats.binary_files += 1
                return file_meta

            # Process text file
            self.stats.text_files += 1
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                file_meta.lines = content.count("\n") + 1
                file_meta.structure = self._analyze_code_structure(file_path, content)

                tokens = self.token_estimator.estimate_tokens(content)
                file_meta.tokens_estimate = tokens

                if tokens > self.config["max_tokens_per_file"]:
                    file_meta.content = self._summarize_large_file(
                        content, file_meta.structure
                    )
                    file_meta.error = "token_limit_exceeded"
                else:
                    file_meta.content = content
                    self.stats.estimated_tokens += tokens

            except OSError as e:  # Catch OS-related errors during text file read
                file_meta.error = f"Error reading file: {e}"
                file_meta.content = f"[{file_meta.error}]"
                self.stats.errors += 1

            return file_meta

        except OSError as e:  # Catch OS-related errors during initial stat/access
            self.stats.errors += 1
            return FileMetadata(
                name=os.path.basename(file_path),
                type="file",
                path=relative_path,
                size=0,
                modified_time="",
                error=f"Error accessing file: {e}",
            )

    def _build_dependency_graph(self, snapshot_tree: Dict) -> Dict[str, List[str]]:
        """Analyze all file structures to build a project dependency graph."""
        if not self.config.get("use_deps"):
            return {}

        dependencies = {}
        file_structures = {}

        def collect_structures(node):
            if node["type"] == "file" and node.get("structure"):
                file_structures[node["path"]] = node["structure"]
            elif node["type"] == "directory" and "children" in node:
                for child in node["children"]:
                    collect_structures(child)

        collect_structures(snapshot_tree)

        project_modules = set(self.module_to_path_map.keys())

        for path, structure in file_structures.items():
            # **FIX**: Use .get() for dictionary access as 'structure' is a dict
            # from asdict()
            if not structure or not structure.get("imports"):
                continue

            local_deps = set()
            base_module_path = os.path.splitext(path)[0].replace(os.sep, ".")
            if base_module_path.endswith(".__init__"):
                base_module_path = base_module_path[:-9]

            for imp in structure.get("imports", []):
                resolved_module = None
                if imp.startswith("."):  # Relative import
                    try:
                        level = 0
                        while imp.startswith("."):
                            level += 1
                            imp = imp[1:]

                        base_parts = base_module_path.split(".")
                        if os.path.basename(path) == "__init__.py":
                            base_parts = base_parts[:-1]

                        if level > len(base_parts): # Invalid relative import (e.g., from ...
                            # import foo at top level)
                            continue

                        prefix = ".".join(base_parts[: len(base_parts) - (level - 1)])

                        if imp:
                            resolved_module = f"{prefix}.{imp}" if prefix else imp
                        else:
                            resolved_module = prefix
                    except Exception:
                        continue
                else:  # Absolute import
                    resolved_module = imp

                if not resolved_module:
                    continue

                # Find the longest matching module in our project
                parts = resolved_module.split(".")
                for i in range(len(parts), 0, -1):
                    potential_module = ".".join(parts[:i])
                    if potential_module in project_modules:
                        local_deps.add(potential_module)
                        break

            if local_deps:
                # Don't list a module as its own dependency
                current_module = os.path.splitext(path)[0].replace(os.sep, ".")
                if current_module.endswith(".__init__"):
                    current_module = current_module[:-9]
                local_deps.discard(current_module)

                if local_deps:
                    dependencies[path] = sorted(list(local_deps))

        return dependencies

    def _count_and_collect_files(
        self,
        root_path: str,
        include_pattern: Optional[re.Pattern],
        exclude_pattern: Optional[re.Pattern],
    ):
        """Pre-scan to count files for progress bar and collect all paths for
        dependency analysis."""
        count = 0
        for root, dirs, files in os.walk(
            root_path, followlinks=self.config["follow_symlinks"]
        ):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for file in files:
                if any(file.endswith(ext) for ext in self.exclude_files):
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, start=root_path)

                if exclude_pattern and exclude_pattern.search(rel_path):
                    continue
                if include_pattern and not include_pattern.search(rel_path):
                    continue

                self.all_file_paths.add(rel_path)
                if rel_path.endswith(".py"):
                    module_path = os.path.splitext(rel_path)[0].replace(os.sep, ".")
                    self.module_to_path_map[module_path] = rel_path
                    if os.path.basename(rel_path) == "__init__.py":
                        package_name = os.path.dirname(module_path)
                        if package_name:
                            self.module_to_path_map[package_name] = rel_path
                count += 1
        return count

    def build_tree(
        self,
        current_dir: str,
        start_path: str,
        include_regex: Optional[str],
        exclude_regex: Optional[str],
        current_depth: int = 0,
    ) -> Dict:
        """Recursively build the directory tree."""
        if current_depth > self.config["max_depth"]:
            return {
                "name": os.path.basename(current_dir),
                "type": "directory",
                "path": os.path.relpath(current_dir, start=start_path),
                "error": "Max depth exceeded",
            }

        include_pattern = re.compile(include_regex) if include_regex else None
        exclude_pattern = re.compile(exclude_regex) if exclude_regex else None

        tree = {
            "name": os.path.basename(current_dir),
            "type": "directory",
            "path": os.path.relpath(current_dir, start=start_path),
            "children": [],
        }

        try:
            os.makedirs(current_dir, exist_ok=True) # Ensure directory exists
            items = sorted(os.listdir(current_dir))
            for item_name in items:
                item_path = os.path.join(current_dir, item_name)
                relative_path = os.path.relpath(item_path, start=start_path)

                is_dir = os.path.isdir(item_path)
                if (is_dir and item_name in self.exclude_dirs) or (
                    not is_dir
                    and any(item_name.endswith(ext) for ext in self.exclude_files)
                ):
                    continue
                if exclude_pattern and exclude_pattern.search(relative_path):
                    continue
                if include_pattern and not include_pattern.search(relative_path):
                    continue

                if is_dir:
                    self.stats.total_directories += 1
                    subtree = self.build_tree(
                        item_path,
                        start_path,
                        include_regex,
                        exclude_regex,
                        current_depth + 1,
                    )
                    if subtree.get("children") or subtree.get("error"):
                        tree["children"].append(subtree)
                else:  # is file
                    self.stats.total_files += 1
                    file_meta = self._process_file(item_path, relative_path)
                    self.stats.total_size += file_meta.size
                    tree["children"].append(asdict(file_meta))
                    if self.progress:
                        self.progress.update()
        except Exception as e:
            tree["error"] = str(e)
            self.stats.errors += 1
        return tree

    def generate_snapshot(
        self,
        root_path: str,
        include_regex: Optional[str] = None,
        exclude_regex: Optional[str] = None,
    ) -> Snapshot:
        """Generate the complete snapshot."""
        self.root_path = os.path.abspath(root_path)
        if not os.path.isdir(self.root_path):
            raise ValueError(f"Root path '{self.root_path}' is not a valid directory")

        print(f"Scanning {self.root_path} with profile '{self.profile}'...")

        git_info = self._get_git_info(self.root_path)

        include_pattern = re.compile(include_regex) if include_regex else None
        exclude_pattern = re.compile(exclude_regex) if exclude_regex else None
        total_files = self._count_and_collect_files(
            self.root_path, include_pattern, exclude_pattern
        )

        if self.config["show_progress"] and total_files > 0:
            self.progress = ProgressTracker(total_files, "Processing files")

        tree = self.build_tree(
            self.root_path, self.root_path, include_regex, exclude_regex
        )

        if self.progress:
            self.progress.complete()
            print()

        dependencies = self._build_dependency_graph(tree)

        metadata = SnapshotMetadata(
            generated_at=datetime.now().isoformat(),
            root_path=self.root_path,
            config=self.config,
            filters={
                "include_regex": include_regex,
                "exclude_regex": exclude_regex,
                "profile": self.profile,
            },
        )

        return Snapshot(
            metadata=metadata,
            statistics=self.stats,
            tree=tree,
            git_info=git_info,
            dependencies=dependencies,
            key_files=sorted(self.key_files),
        )

    def export_json(self, snapshot: Snapshot, pretty: bool = False) -> str:
        """Export snapshot as JSON."""
        return json.dumps(
            asdict(snapshot), indent=2 if pretty else None, ensure_ascii=False
        )

    def export_markdown(self, snapshot: Snapshot) -> str:
        """Export snapshot as a comprehensive markdown file."""
        md = [f"# Snapshot of `{os.path.basename(snapshot.metadata.root_path)}`"]
        md.append(
            f"> Generated at {snapshot.metadata.generated_at} with paleaepro v"
            f"{snapshot.metadata.tool_version}\n"
        )

        # --- Git Info ---
        if snapshot.git_info and not snapshot.git_info.error:
            md.append("## Git Status")
            md.append(f"- **Branch:** `{snapshot.git_info.branch}`")
            if snapshot.git_info.recent_commits:
                md.append("- **Recent Commits:")
                md.extend([f"  - `{c}`" for c in snapshot.git_info.recent_commits])
            if snapshot.git_info.status:
                md.append("- **Status (`git status --porcelain`):**")
                md.append("```")
                md.append(snapshot.git_info.status)
                md.append("```")
            md.append("")

        # --- Summary & Key Files ---
        md.append("## Project Summary")
        stats = snapshot.statistics
        md.append(
            f"- **Total Files:** {stats.total_files} ({stats.text_files} text, "
            f"{stats.binary_files} binary)"
        )
        md.append(f"- **Total Dirs:** {stats.total_directories}")
        md.append(f"- **Total Size:** {stats.total_size / 1024:.2f} KB")
        md.append(f"- **Estimated Tokens:** ~{stats.estimated_tokens:,}")
        if snapshot.key_files:
            md.append("- **Key Files:")
            md.extend([f"  - `{f}`" for f in snapshot.key_files])
        md.append("")

        # --- Dependency Graph ---
        if snapshot.dependencies:
            md.append("## Dependency Graph")
            md.append("```mermaid")
            md.append("graph TD")
            for path, deps in snapshot.dependencies.items():
                for dep in deps:
                    dep_path = self.module_to_path_map.get(dep)
                    if dep_path:
                        md.append(f'    "{path}" --> "{dep_path}"')
            md.append("```")
            md.append("")

        # --- File Tree ---
        md.append("## File Tree")
        md.append("```")
        md.extend(self._tree_to_text(snapshot.tree))
        md.append("```")
        md.append("")

        # --- File Contents ---
        md.append("## File Contents")
        md.extend(self._extract_file_contents_md(snapshot.tree))

        return "\n".join(md)

    def _tree_to_text(
        self,
        tree: Dict,
        prefix: str = "",
        is_last: bool = True,
    ) -> List[str]:
        """Helper to convert tree dict to text."""
        connector = "└── " if is_last else "├── "
        name = tree["name"]
        if tree["type"] == "directory":
            name = f"{name}"
        elif tree.get("is_binary"):
            name = f"{name}"
        else:
            name = f"{name}"

        lines = [f"{prefix}{connector}{name}"]
        if tree["type"] == "directory" and "children" in tree:
            extension = "    " if is_last else "│   "
            for i, child in enumerate(tree["children"]):
                lines.extend(
                    self._tree_to_text(
                        child,
                        prefix + extension,
                        i == len(tree["children"]) - 1,
                    )
                )
        return lines

    def _extract_file_contents_md(self, tree: Dict) -> List[str]:
        """Helper to format file contents for markdown."""
        md = []
        if tree["type"] == "file" and tree.get("content"):
            if not tree.get("is_binary"):
                lang = os.path.splitext(tree["name"])[1].lstrip(".") or "text"
                md.append(f"### `{tree['path']}`")

                info = [f"Size: {tree['size'] / 1024:.2f} KB"]
                if tree.get("tokens_estimate"):
                    info.append(f"Tokens: ~{tree['tokens_estimate']}")
                md.append(f"*{' | '.join(info)}*")

                if tree.get("structure"):
                    s = tree["structure"]
                    md.append("```yaml")
                    md.append("# Code Structure")
                    if s.get("classes"):
                        md.append(f"classes: {[c['name'] for c in s['classes']]}")
                    if s.get("functions"):
                        md.append(f"functions: {[f['name'] for f in s['functions']]}")
                    if s.get("imports"):
                        md.append(f"imports: {len(s['imports'])}")
                    md.append("```")

                md.append(f"```{lang}")
                md.append(tree["content"])
                md.append("```")
                md.append("")
        elif tree["type"] == "directory" and "children" in tree:
            for child in tree["children"]:
                md.extend(self._extract_file_contents_md(child))
        return md

    def export_zip(self, snapshot: Snapshot, output_path: str) -> None:
        """Export snapshot as a ZIP file with JSON and markdown versions."""
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # Add JSON version
            json_content = self.export_json(snapshot, pretty=True)
            zipf.writestr("snapshot.json", json_content)

            # Add markdown version
            md_content = self.export_markdown(snapshot)
            zipf.writestr("snapshot.md", md_content)

            # Add metadata file
            metadata = {
                "tool_version": snapshot.metadata.tool_version,
                "generated_at": snapshot.metadata.generated_at,
                "root_path": snapshot.metadata.root_path,
                "profile": snapshot.metadata.filters.get("profile", "minimal"),
                "stats": asdict(snapshot.statistics),
            }
            zipf.writestr("metadata.json", json.dumps(metadata, indent=2))


# --- CLI Interface ---


def main():
    """Main CLI interface with comprehensive options."""
    # **FIX**: Use a raw string for epilog to avoid SyntaxWarning
    parser = argparse.ArgumentParser(
        description="PalaePro Directory Snapshot Tool for AI Coding Assistants "
        "(v3.0.2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=r"""
Examples:
  %(prog)s                              # Snapshot current directory with
                                       # minimal profile
  %(prog)s --profile ai_optimized       # Use AI-optimized exclusions
  %(prog)s --format markdown            # Export as markdown
  %(prog)s -o snapshot.zip              # Export as ZIP bundle (format is
                                       # inferred from extension)
  %(prog)s --include "\.py$"            # Include only Python files
  %(prog)s --exclude "test_.*"          # Exclude test files
  %(prog)s --estimate                   # Show profile impact estimation and exit
  %(prog)s --config my_config.ini       # Use custom configuration
  %(prog)s --no-git --no-deps           # Disable git and dependency analysis
  %(prog)s /path/to/project --tokens 16000  # Custom token limit per file
  %(prog)s --model-profile flash        # Optimize for Google 2.5 Flash

Profiles:
  minimal      - Basic exclusions (.git, __pycache__, node_modules, etc.)
  ai_optimized - Extended exclusions for AI context optimization

Model Profiles:
  default      - Standard token limits (8000 tokens per file)
  flash        - Optimized for Google 2.5 Flash (128000 tokens per file)
  pro          - Optimized for Google 2.5 Pro (256000 tokens per file)
""",
    )

    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Directory to snapshot (default: current directory)",
    )
    parser.add_argument(
        "--profile",
        choices=["minimal", "ai_optimized", "gemini_optimized"],
        default="minimal",
        help="Exclusion profile to use (default: minimal)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "zip"],
        help="Output format (default: json, or inferred from -o extension)",
    )
    parser.add_argument("--output", "-o", help="Output file path (default: stdout for json/markdown)")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--include", help="Include regex pattern")
    parser.add_argument("--exclude", help="Exclude regex pattern")
    parser.add_argument(
        "--estimate",
        action="store_true",
        help="Show profile impact estimation and exit",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    parser.add_argument(
        "--no-progress", action="store_true", help="Disable progress indicators"
    )
    parser.add_argument("--no-git", action="store_true", help="Disable git integration")
    parser.add_argument(
        "--no-deps", action="store_true", help="Disable dependency analysis"
    )
    parser.add_argument(
        "--no-ast", action="store_true", help="Disable AST code structure analysis"
    )
    parser.add_argument(
        "--tokens",
        type=int,
        help="Max tokens per file before summarization (default: 8000)",
    )
    parser.add_argument(
        "--max-size", type=int, help="Max file size in bytes (default: 1MB)"
    )
    parser.add_argument(
        "--max-depth", type=int, help="Maximum directory depth (default: 20)"
    )
    parser.add_argument(
        "--follow-symlinks", action="store_true", help="Follow symbolic links"
    )
    parser.add_argument(
        "--version", action="version", version="PalaePro v3.0.2"
    )
    parser.add_argument(
        "--model-profile",
        choices=["flash", "pro", "default"],
        default="default",
        help="Optimize snapshot for a specific AI model (e.g., flash, pro)",
    )

    args = parser.parse_args()

    # Handle estimation mode
    if args.estimate:
        TokenEstimator.estimate_profile_impact(os.path.abspath(args.directory))
        return

    # Determine output format
    output_format = args.format
    if not output_format and args.output:
        ext = os.path.splitext(args.output)[1].lower()
        if ext == ".json":
            output_format = "json"
        elif ext in [".md", ".markdown"]:
            output_format = "markdown"
        elif ext == ".zip":
            output_format = "zip"
    if not output_format:
        output_format = "json"  # Default format

    # Initialize paleaepro with configuration
    paleaepro = PalaePro(
        config_file=args.config, profile=args.profile, model_profile=args.model_profile
    )

    # Apply CLI overrides to the loaded config
    if args.no_progress:
        paleaepro.config["show_progress"] = False
    if args.no_git:
        paleaepro.config["use_git"] = False
    if args.no_deps:
        paleaepro.config["use_deps"] = False
    if args.no_ast:
        paleaepro.config["use_ast"] = False
    if args.tokens is not None:
        paleaepro.config["max_tokens_per_file"] = args.tokens
    if args.max_size is not None:
        paleaepro.config["max_file_size"] = args.max_size
    if args.max_depth is not None:
        paleaepro.config["max_depth"] = args.max_depth
    if args.follow_symlinks:
        paleaepro.config["follow_symlinks"] = True

    try:
        # Generate snapshot
        snapshot = paleaepro.generate_snapshot(
            root_path=args.directory,
            include_regex=args.include,
            exclude_regex=args.exclude,
        )

        # Export in requested format
        if output_format == "json":
            output = paleaepro.export_json(snapshot, pretty=args.pretty)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"JSON snapshot saved to: {args.output}")
            else:
                print(output)

        elif output_format == "markdown":
            output = paleaepro.export_markdown(snapshot)
            if args.output:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"Markdown snapshot saved to: {args.output}")
            else:
                print(output)

        elif output_format == "zip":
            output_path =
                args.output
                or f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            paleaepro.export_zip(snapshot, output_path)
            print(f"ZIP bundle saved to: {output_path}")

        # Print summary to stderr
        stats = snapshot.statistics
        summary_lines = [
            "\n---",
            "Snapshot Summary:",
            f"   - Files: {stats.total_files} ({stats.text_files} text, "
            f"{stats.binary_files} binary)",
            f"   - Directories: {stats.total_directories}",
            f"   - Size: {stats.total_size / 1024:.2f} KB",
            f"   - Estimated Tokens: ~{stats.estimated_tokens:,}",
        ]
        if stats.errors:
            summary_lines.append(f"   - Errors: {stats.errors}")
        if snapshot.key_files:
            summary_lines.append(f"   - Key Files: {len(snapshot.key_files)}")
        print("\n".join(summary_lines), file=sys.stderr)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


# --- Interactive Mode ---


def interactive_mode():
    """Interactive mode for non-technical users."""
    print("PalaePro Interactive Mode")
    print("=" * 40)

    try:
        directory =
            input("Directory to snapshot (press Enter for current): ").strip() or "."

        print("\nAvailable profiles:")
        print("   1. minimal      - Basic exclusions (good for most projects)")
        print("   2. ai_optimized - More aggressive exclusions (best for AI analysis)")
        # **FIX**: Correctly set profile based on user input
        profile_choice = input("Choose profile (1-2, default: 2): ").strip()
        profile = "minimal" if profile_choice == "1" else "ai_optimized"

        print("\nOutput formats:")
        print("   1. JSON      - Machine-readable")
        print("   2. Markdown  - Human-readable (recommended)")
        print("   3. ZIP       - Bundle with both formats")
        format_map = {"1": "json", "2": "markdown", "3": "zip"}
        output_format = format_map.get(
            input("Choose format (1-3, default: 2): ").strip(), "markdown"
        )

        default_ext = {"json": ".json", "markdown": ".md", "zip": ".zip"}
        default_filename = f"snapshot{default_ext[output_format]}"
        prompt =
            f"\nOutput file (press Enter for "
            f"{'stdout' if output_format != 'zip' else default_filename}): "
        output_file = input(prompt).strip()
        if not output_file and output_format == "zip":
            output_file = default_filename

        print(
            f"\nAnalyzing '{os.path.abspath(directory)}' with '{profile}' profile..."
        )
        TokenEstimator.estimate_profile_impact(directory, [profile])

        proceed = input("\nProceed with snapshot generation? (Y/n): ").strip().lower()
        if proceed == "n":
            print("Operation cancelled.")
            return

        paleaepro = PalaePro(profile=profile)
        snapshot = paleaepro.generate_snapshot(directory)

        if output_format == "zip":
            paleaepro.export_zip(snapshot, output_file)
            print(f"Snapshot bundle saved to: {output_file}")
        else:
            output =
                paleaepro.export_json(snapshot, pretty=True)
                if output_format == "json"
                else paleaepro.export_markdown(snapshot)
            if output_file:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output)
                print(f"\nSnapshot saved to: {output_file}")
            else:
                print("\n" + "=" * 20 + " SNAPSHOT START " + "=" * 20)
                print(output)
                print("=" * 21 + " SNAPSHOT END " + "=" * 21)

    except (KeyboardInterrupt, EOFError):
        print("\n\nOperation cancelled. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback

        traceback.print_exc(file=sys.stderr)


# --- Entry Point ---

if __name__ == "__main__":
    # If run with no arguments in an interactive terminal, start interactive mode
    if len(sys.argv) == 1 and sys.stdin.isatty():
        interactive_mode()
    else:
        main()