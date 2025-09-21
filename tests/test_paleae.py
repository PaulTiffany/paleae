# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Paul Tiffany
# Project: paleae - Snapshot your repo for LLMs

"""
Unit and property-based tests for paleae.py.

This test suite ensures the reliability and determinism of paleae, a tool designed
to create clean, structured, and AI-optimized snapshots of code repositories. The
tests cover everything from file parsing and filtering to the integrity of the final
JSON/JSONL output.

The core principle tested here is that paleae must be a trustworthy preprocessor
for AI analysis. A high-quality, predictable snapshot is the foundation for any
meaningful interaction between a Large Language Model and a codebase. These tests
validate that foundation.
"""

import argparse
import fnmatch
import importlib.util
import json
import re
import runpy
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


def load_paleae_module():
    """Load the paleae.py script as a module."""
    script_path = Path(__file__).parent.parent / "paleae.py"
    spec = importlib.util.spec_from_file_location("paleae", script_path)
    if not (spec and spec.loader):
        raise ImportError(f"Could not load spec for module paleae from {script_path}")
    paleae = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(paleae)
    sys.modules["paleae"] = paleae
    return paleae


paleae = load_paleae_module()


# --- Fixtures ---


@pytest.fixture
def temp_repo(tmp_path: Path):
    """Create a temporary directory structure for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "src").mkdir()
    (repo / "tests").mkdir()
    (repo / ".git").mkdir()
    (repo / "venv").mkdir()
    (repo / "__pycache__").mkdir()
    (repo / ".paleaeignore").write_text(
        """# Ignore logs
*.log

!important.log
dist/
"""
    )
    (repo / "src" / "main.py").write_text("print('hello')")
    (repo / "src" / "utils.py").write_text("def helper(): pass")
    (repo / "README.md").write_text("# My Project")
    (repo / "data.bin").write_bytes(b"\x00\x01\x02")
    (repo / "empty.txt").touch()
    (repo / "app.log").write_text("Log entry")
    (repo / "important.log").write_text("Important log")
    (repo / "dist").mkdir()
    (repo / "dist" / "package.tar.gz").touch()
    (repo / "tests" / "test_main.py").write_text("assert True")

    # Create a file with unicode errors
    (repo / "bad_encoding.txt").write_bytes(b"\xff\xfe")

    # Create a file that is too large
    large_file = repo / "large_file.txt"
    with large_file.open("wb") as f:
        f.seek(paleae.MAX_SIZE + 1)
        f.write(b"\0")

    return repo


# --- Unit Tests for Core Logic ---


def test_importer_failure():
    """Test the script importer fails gracefully."""
    with patch("importlib.util.spec_from_file_location", return_value=None):
        with pytest.raises(ImportError):
            load_paleae_module()


def test_token_estimate():
    assert paleae.token_estimate("") == 0
    assert paleae.token_estimate("a") == 1
    assert paleae.token_estimate("abc") == 1
    assert paleae.token_estimate("abcd") == 1
    assert paleae.token_estimate("abcde") == 1
    long_text = "long text for estimation"
    assert paleae.token_estimate(long_text) == len(long_text) // 4
    assert paleae.token_estimate(None) == 0


@given(st.text())
def test_token_estimate_hypothesis(s):
    """Property-based test for token_estimate."""
    estimate = paleae.token_estimate(s)
    assert isinstance(estimate, int)
    assert estimate >= 0
    if s:
        assert estimate > 0
        assert estimate >= len(s) // 4
    else:
        assert estimate == 0


def test_is_text_file(temp_repo):
    assert paleae.is_text_file(temp_repo / "src" / "main.py") is True
    assert paleae.is_text_file(temp_repo / "README.md") is True
    assert paleae.is_text_file(temp_repo / "data.bin") is False
    assert paleae.is_text_file(temp_repo / "empty.txt") is True
    (temp_repo / "empty_no_ext").touch()
    assert paleae.is_text_file(temp_repo / "empty_no_ext") is True
    assert paleae.is_text_file(temp_repo / "non_existent_file.txt") is False
    assert paleae.is_text_file(temp_repo / "bad_encoding.txt") is False
    assert paleae.is_text_file(temp_repo / "large_file.txt") is False
    # Test a file with a non-text extension but text content
    (temp_repo / "custom.ext").write_text("text content")
    assert paleae.is_text_file(temp_repo / "custom.ext") is True
    # Test directory
    assert paleae.is_text_file(temp_repo / "src") is False
    # Test permission error on read
    with patch.object(Path, "open", side_effect=PermissionError):
        assert paleae.is_text_file(temp_repo / "src" / "main.py") is False


# Strategy for content that is likely not UTF-8
invalid_utf8_content = st.text(min_size=1).map(lambda s: s.encode("utf-16"))


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(content=invalid_utf8_content)
def test_is_text_file_invalid_utf8_hypothesis(tmp_path, content):
    # Ensure we don't have null bytes, to isolate the unicode error
    content = content.replace(b"\x00", b"")
    if not content:
        return  # Skip if the content becomes empty after removing nulls

    path = tmp_path / "invalid_utf8.txt"
    path.write_bytes(content)

    # is_text_file should return False because of UnicodeDecodeError
    assert not paleae.is_text_file(path)


def test_translate_globs_to_regex():
    globs = ["*.py", "src/", "# comment", "", "data[0-9].bin"]
    expected = [
        fnmatch.translate("*.py"),
        fnmatch.translate("src/"),
        fnmatch.translate("data[0-9].bin"),
    ]
    assert paleae._translate_globs_to_regex(globs) == expected


# Characters that have special meaning in globs but not always in regex
st_glob_chars = st.sampled_from("*?[]!")

# Strategy for generating a simple glob pattern component
st_glob_part = st.text(
    st.characters(max_codepoint=127, blacklist_characters="*?[]!/\\"),
    min_size=1,
)


# Strategy for generating a full glob pattern
st_glob_pattern = st.lists(st.one_of(st_glob_part, st_glob_chars), min_size=1, max_size=10).map(
    "".join
)


@given(pattern=st_glob_pattern, text=st.text(max_size=100))
def test_translate_globs_to_regex_hypothesis(pattern, text):
    """Check that translated glob regex behaves like fnmatch."""
    # The core invariant: if fnmatch.fnmatch matches, so should the regex.
    # Note: The reverse is not always true due to how fnmatch translates '**' etc.
    # We are testing for basic consistency.
    try:
        regex_str = fnmatch.translate(pattern)
        # On Windows, fnmatch is case-insensitive by default.
        flags = re.IGNORECASE if sys.platform == "win32" else 0
        compiled_regex = re.compile(regex_str, flags)

        matches_glob = fnmatch.fnmatch(text, pattern)
        matches_regex = compiled_regex.match(text) is not None

        if matches_glob:
            assert matches_regex, (
                f"Glob '{pattern}' matched '{text}', but regex '{regex_str}' did not."
            )

    except re.error:
        # Some generated patterns might be invalid for fnmatch, which is fine.
        # We are interested in the behavior of valid patterns.
        pass


def test_read_paleaeignore(temp_repo):
    pos, neg = paleae.read_paleaeignore(temp_repo)
    assert pos == ["*.log", "dist/"]
    assert neg == ["important.log"]


def test_read_paleaeignore_not_found(tmp_path):
    pos, neg = paleae.read_paleaeignore(tmp_path)
    assert pos == []
    assert neg == []


def test_read_paleaeignore_permission_error(temp_repo, capsys):
    with patch.object(Path, "read_text", side_effect=PermissionError("Permission denied")):
        pos, neg = paleae.read_paleaeignore(temp_repo)
        assert pos == []
        assert neg == []
        captured = capsys.readouterr()
        assert f"Warning: Could not read {paleae.PALEAEIGNORE}" in captured.err


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    lines=st.lists(
        st.one_of(
            st.just(""),  # Empty lines
            st.just("# comment"),  # Comments
            st.just("!negated"),  # Negated pattern
            st.just("  ! spaced_negated  "),  # Spaced negated
            st.just("positive"),  # Positive pattern
            st.just("  spaced_positive  "),  # Spaced positive
        )
    )
)
def test_read_paleaeignore_hypothesis(tmp_path, lines):
    """Test parsing of .paleaeignore with varied content."""
    content = "\n".join(lines)
    ignore_file = tmp_path / paleae.PALEAEIGNORE
    ignore_file.write_text(content)

    pos, neg = paleae.read_paleaeignore(tmp_path)

    expected_pos = []
    expected_neg = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("!"):
            expected_neg.append(stripped[1:].strip())
        else:
            expected_pos.append(stripped)

    assert sorted(pos) == sorted(expected_pos)
    assert sorted(neg) == sorted(expected_neg)


def test_compile_patterns():
    patterns = ["^src/", r"\.py$"]
    compiled = paleae.compile_patterns(patterns)
    assert len(compiled) == len(patterns)
    assert compiled[0].pattern == "^src/"
    assert compiled[1].pattern == r"\.py$"
    assert paleae.compile_patterns(None) == []


def test_compile_patterns_invalid_regex():
    with pytest.raises(paleae.PaleaeError, match="unterminated character set"):
        paleae.compile_patterns(["["])


def test_matches_any():
    patterns = [re.compile(r"^src/"), re.compile(r"\.md$")]
    assert paleae.matches_any("src/main.py", patterns) is True
    assert paleae.matches_any("README.md", patterns) is True
    assert paleae.matches_any("tests/test.py", patterns) is False


@given(
    text=st.text(max_size=100),
    patterns_str=st.lists(st.sampled_from([r"^a", r"b$", r"c\d"]), min_size=0, max_size=5),
)
def test_matches_any_hypothesis(text, patterns_str):
    """Test matches_any logic against a manual check."""
    patterns = [re.compile(p) for p in patterns_str]

    result = paleae.matches_any(text, patterns)

    manual_check = any(re.search(p, text) for p in patterns_str)

    assert result == manual_check


# --- Integration-like Tests for File Collection ---


def test_collect_files_default_skip(temp_repo):
    all_files = [p.relative_to(temp_repo).as_posix() for p in temp_repo.rglob("*") if p.is_file()]
    exc_patterns = paleae.compile_patterns(paleae.DEFAULT_SKIP)
    expected = [
        f
        for f in all_files
        if not paleae.matches_any(f, exc_patterns) and paleae.is_text_file(temp_repo / f)
    ]
    files = paleae.collect_files(temp_repo, [], exc_patterns, [], [])
    assert sorted(files) == sorted(expected)


def test_collect_files_with_paleaeignore(temp_repo):
    pos_globs, neg_globs = paleae.read_paleaeignore(temp_repo)
    ign_pos_rx = paleae.compile_patterns(paleae._translate_globs_to_regex(pos_globs))
    ign_neg_rx = paleae.compile_patterns(paleae._translate_globs_to_regex(neg_globs))
    files = paleae.collect_files(
        temp_repo,
        [],
        paleae.compile_patterns(paleae.DEFAULT_SKIP),
        ign_pos_rx,
        ign_neg_rx,
    )
    assert "app.log" not in files
    assert not any(f.startswith("dist/") for f in files)
    assert "important.log" in files
    assert "src/main.py" in files


def test_collect_files_with_cli_include_exclude(temp_repo):
    inc = paleae.compile_patterns([r"^src/"])
    exc = paleae.compile_patterns([r"\.py$"])
    files = paleae.collect_files(temp_repo, inc, exc, [], [])
    assert files == []
    inc = paleae.compile_patterns([r"^src/"])
    exc = paleae.compile_patterns([r"utils"])
    files = paleae.collect_files(temp_repo, inc, exc, [], [])
    assert files == ["src/main.py"]


def test_collect_files_non_existent_dir():
    with pytest.raises(paleae.PaleaeError, match="Directory not found"):
        paleae.collect_files(Path("nonexistent"), [], [], [], [])


def test_collect_files_permission_error(temp_repo):
    with patch.object(Path, "rglob", side_effect=PermissionError("Access denied")):
        with pytest.raises(paleae.PaleaeError, match="Error traversing"):
            paleae.collect_files(temp_repo, [], [], [], [])


def test_collect_files_value_error_on_relative_to(temp_repo):
    with patch.object(Path, "relative_to", side_effect=ValueError):
        files = paleae.collect_files(temp_repo, [], [], [], [])
        assert files is not None


# --- Tests for Snapshot Building and Writing ---


def test_build_snapshot(temp_repo):
    files = ["src/main.py", "README.md", "non_existent.txt"]
    ignore_meta = {"file": ".paleaeignore", "present": True, "patterns": 2, "negations": 1}
    with patch("time.strftime", return_value="2025-09-14T12:00:00Z"):
        data = paleae.build_snapshot(temp_repo, files, ignore_meta)

    assert data["meta"]["tool"] == "paleae"
    assert data["meta"]["version"] == paleae.__version__
    assert data["meta"]["timestamp"] == "2025-09-14T12:00:00Z"
    assert data["meta"]["root_directory"] == str(temp_repo)
    assert data["meta"]["ignore_file"] == ignore_meta

    expected_file_count = 2
    assert len(data["files"]) == expected_file_count

    main_py_data = next(f for f in data["files"] if f["path"] == "src/main.py")
    readme_data = next(f for f in data["files"] if f["path"] == "README.md")
    content = "print('hello')"
    assert main_py_data["content"] == content
    assert main_py_data["size_chars"] == len(content)
    assert main_py_data["estimated_tokens"] > 0
    assert readme_data["content"] == "# My Project"

    summary = data["meta"]["summary"]
    assert summary["total_files"] == expected_file_count

    expected_total_chars = main_py_data["size_chars"] + readme_data["size_chars"]
    assert summary["total_chars"] == expected_total_chars

    expected_total_tokens = main_py_data["estimated_tokens"] + readme_data["estimated_tokens"]
    assert summary["estimated_tokens"] == expected_total_tokens


def test_build_snapshot_skips_empty_files(temp_repo):
    (temp_repo / "truly_empty.txt").touch()
    (temp_repo / "whitespace.txt").write_text("   \n\t   ")
    files = ["truly_empty.txt", "whitespace.txt"]
    data = paleae.build_snapshot(temp_repo, files, {})
    assert len(data["files"]) == 0


def test_build_snapshot_read_error(temp_repo):
    with patch.object(Path, "read_text", side_effect=OSError("Read error")):
        data = paleae.build_snapshot(temp_repo, ["src/main.py"], {})
        assert len(data["files"]) == 0


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    file_contents=st.dictionaries(
        keys=st.text(
            st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=10
        ).map(lambda s: f"{s}.txt"),
        values=st.text(min_size=1, max_size=1000),  # Ensure content is not empty
        min_size=1,
        max_size=10,
    )
)
def test_build_snapshot_summary_invariant(tmp_path, file_contents):
    """The summary metadata must accurately reflect the file data."""
    # Create the files in a temp directory
    for rel_path, content in file_contents.items():
        file_path = tmp_path / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")

    rel_files = sorted(list(file_contents.keys()))

    # Build the snapshot
    snapshot = paleae.build_snapshot(tmp_path, rel_files, {})

    # Verify the invariant
    summary = snapshot["meta"]["summary"]
    files_data = snapshot["files"]

    assert summary["total_files"] == len(files_data)

    # We need to recalculate totals from the *actual* files included,
    # as some might have been skipped (e.g., if they became empty after stripping)
    included_paths = {f["path"] for f in files_data}

    expected_chars = sum(len(file_contents[p]) for p in included_paths)
    expected_tokens = sum(paleae.token_estimate(file_contents[p]) for p in included_paths)

    assert summary["total_chars"] == expected_chars
    assert summary["estimated_tokens"] == expected_tokens


def test_write_output_json(tmp_path):
    out_path = tmp_path / "snapshot.json"
    data = {"meta": {"tool": "paleae"}, "files": [{"path": "a.py"}]}
    paleae.write_output(out_path, data, "json")
    content = json.loads(out_path.read_text())
    assert content["meta"]["tool"] == "paleae"
    assert content["files"][0]["path"] == "a.py"


def test_write_output_jsonl(tmp_path):
    out_path = tmp_path / "snapshot.jsonl"
    file_data = [
        {"path": "a.py", "content": "a"},
        {"path": "b.py", "content": "b"},
    ]
    data = {"meta": {"tool": "paleae", "version": "1.0.0"}, "files": file_data}
    paleae.write_output(out_path, data, "jsonl")
    lines = out_path.read_text().strip().split("\n")

    expected_line_count = 1 + len(file_data)  # 1 meta line + file lines
    assert len(lines) == expected_line_count

    meta = json.loads(lines[0])
    file1 = json.loads(lines[1])
    file2 = json.loads(lines[2])
    assert meta["type"] == "meta"
    assert meta["tool"] == "paleae"
    assert file1["type"] == "file"
    assert file1["path"] == "a.py"
    assert file2["path"] == "b.py"


def test_write_output_permission_error(tmp_path):
    out_path = tmp_path / "snapshot.json"
    with patch.object(Path, "write_text", side_effect=PermissionError("Access denied")):
        with pytest.raises(paleae.PaleaeError, match="Error writing"):
            paleae.write_output(out_path, {"meta": {}, "files": []}, "json")


# --- Tests for CLI and Main Execution ---


@patch("paleae.write_output")
@patch("paleae.build_snapshot")
@patch("paleae.collect_files")
def test_main_success(mock_collect, mock_build, mock_write, temp_repo, capsys):
    mock_collect.return_value = ["src/main.py"]
    mock_build.return_value = {
        "meta": {
            "summary": {
                "total_files": 1,
                "total_chars": 100,
                "estimated_tokens": 25,
            }
        },
        "files": [{"path": "src/main.py"}],
    }
    with patch("sys.argv", ["paleae", str(temp_repo)]):
        assert paleae.main() == 0
    mock_collect.assert_called_once()
    mock_build.assert_called_once()
    mock_write.assert_called_once()
    captured = capsys.readouterr()
    assert "Snapshot saved to" in captured.out
    assert "Files: 1" in captured.out
    assert "Characters: 100" in captured.out
    assert "Tokens: 25" in captured.out


def test_main_about(capsys):
    with patch("sys.argv", ["paleae", "--about"]):
        assert paleae.main() == 0
    captured = capsys.readouterr()
    assert f"paleae {paleae.__version__}" in captured.out
    assert paleae.__website__ in captured.out
    assert paleae.__source__ in captured.out


def test_main_invalid_directory(capsys):
    with patch("sys.argv", ["paleae", "non_existent_dir"]):
        assert paleae.main() == 1
    captured = capsys.readouterr()
    assert "is not a directory" in captured.err


def test_main_no_files_found(temp_repo, capsys):
    with patch("paleae.collect_files", return_value=[]):
        with patch("sys.argv", ["paleae", str(temp_repo)]):
            assert paleae.main() == 1
    captured = capsys.readouterr()
    assert "No text files found" in captured.err


def test_main_paleae_error(capsys):
    with patch("paleae.collect_files", side_effect=paleae.PaleaeError("Test error")):
        with patch("sys.argv", ["paleae", "."]):
            assert paleae.main() == 1
    captured = capsys.readouterr()
    assert "Error: Test error" in captured.err


def test_main_keyboard_interrupt(capsys):
    with patch("paleae.collect_files", side_effect=KeyboardInterrupt):
        with patch("sys.argv", ["paleae", "."]):
            assert paleae.main() == 1
    captured = capsys.readouterr()
    assert "Cancelled by user" in captured.err


def test_main_unexpected_exception(capsys):
    with patch("paleae.collect_files", side_effect=ValueError("Unexpected")):
        with patch("sys.argv", ["paleae", "."]):
            assert paleae.main() == 1
    captured = capsys.readouterr()
    assert "Unexpected error: Unexpected" in captured.err


def test_create_parser():
    parser = paleae.create_parser()
    assert isinstance(parser, argparse.ArgumentParser)
    actions = {action.dest: action for action in parser._actions}
    assert "directory" in actions
    assert "out" in actions
    assert "format" in actions
    assert "version" in actions
    assert "about" in actions


def test_main_with_output_file(temp_repo, capsys):
    output_file = temp_repo / "output.json"
    with patch("sys.argv", ["paleae", str(temp_repo), "-o", str(output_file)]):
        with patch("paleae.collect_files", return_value=["README.md"]):
            with patch(
                "paleae.build_snapshot",
                return_value={
                    "meta": {
                        "summary": {
                            "total_files": 1,
                            "total_chars": 12,
                            "estimated_tokens": 3,
                        }
                    },
                    "files": [{"path": "README.md"}],
                },
            ):
                paleae.main()
    assert output_file.exists()
    captured = capsys.readouterr()
    assert f"Snapshot saved to {output_file}" in captured.out


def test_main_profile_and_extra_patterns(temp_repo):
    with patch(
        "sys.argv",
        [
            "paleae",
            str(temp_repo),
            "--profile",
            "ai_optimized",
            "--include",
            r"\.md$",
            "--exclude",
            "src",
        ],
    ):
        with patch("paleae.collect_files", return_value=[]) as mock_collect:
            paleae.main()
            args, kwargs = mock_collect.call_args
            inc_patterns = args[1]
            exc_patterns = args[2]
            assert len(inc_patterns) == len(paleae.PROFILES["ai_optimized"]["include"]) + 1
            assert len(exc_patterns) == len(paleae.PROFILES["ai_optimized"]["exclude"]) + 1
            assert any(p.pattern == r"\.md$" for p in inc_patterns)
            assert any(p.pattern == "src" for p in exc_patterns)


def test_main_entrypoint():
    """Test running the script directly."""
    script_path = Path(__file__).parent.parent / "paleae.py"
    result = subprocess.run(
        [sys.executable, str(script_path), "--about"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert paleae.__version__ in result.stdout
    assert paleae.__website__ in result.stdout


# This is a placeholder to allow running the file directly
if __name__ == "__main__":
    pytest.main()


def test_main_runpy_about(capsys):
    """Execute paleae.py as __main__ in-process so coverage hits the guard line."""
    script_path = Path(__file__).parent.parent / "paleae.py"
    with patch("sys.argv", ["paleae.py", "--about"]):
        with patch("sys.exit") as mock_exit:
            runpy.run_path(str(script_path), run_name="__main__")
            mock_exit.assert_called_once_with(0)
    out = capsys.readouterr().out
    # Sanity: --about should print version + website
    assert "paleae" in out and paleae.__version__ in out and paleae.__website__ in out


def test_testfile_main_entry():
    """Cover the __main__ block in the test file itself."""
    with patch("pytest.main", return_value=0) as mock_pytest_main:
        runpy.run_path(str(Path(__file__)), run_name="__main__")
        mock_pytest_main.assert_called_once()
