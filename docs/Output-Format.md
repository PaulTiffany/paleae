# Output Format

Paleae generates structured output in JSON or JSONL format, optimized for AI analysis and programmatic processing.

## Format Overview

### JSON Format (Default)
A single JSON object containing metadata and a list of all files.
```json
{
  "meta": {},
  "files": []
}
```
**Best for**: Small to medium repositories, human inspection, and tools that require a complete JSON object.

### JSONL Format
Line-delimited JSON, with one object per line.
```json
{"type":"meta","tool":"paleae"}
{"type":"file","path":"src/main.py"}
{"type":"file","path":"README.md"}
```
**Best for**: Large repositories, streaming processing, and memory efficiency. See [Advanced Usage](Advanced-Usage) for examples.

---

## Metadata Structure (`meta`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `tool` | string | Always "paleae". |
| `version` | string | The version of Paleae used. |
| `timestamp` | string | ISO 8601 UTC timestamp of generation. |
| `root_directory` | string | Absolute path to the scanned directory. |
| `ignore_file` | object | Information about the `.paleaeignore` file. See [Configuration](Configuration). |
| `summary` | object | Aggregate statistics for the snapshot. |

---

## File Object Structure (`files`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `path` | string | The relative path to the file from the root. |
| `content` | string | The full content of the file. |
| `size_chars` | integer | The number of characters in the file. |
| `sha256` | string | A SHA-256 hash of the file content for integrity checks. |
| `estimated_tokens` | integer | An approximate token count (based on character count). |

### Path Normalization
- Paths always use forward slashes (`/`).
- Paths are relative to the repository root (e.g., `src/main.py`).

### Hash Verification
The SHA-256 hash allows you to verify content integrity and detect changes between snapshots, as mentioned in the [FAQ](FAQ).

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
