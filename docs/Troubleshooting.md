# Troubleshooting

Common issues and solutions for Paleae.

[< Back to Wiki Home](Home)

## "No text files found matching criteria"

This is the most common issue and usually means your filtering is too restrictive.

- **Check your directory**: Make sure you are running Paleae in a directory that actually contains code.
- **Test with a broad pattern**: Try `python paleae.py --include ".*"`. See the [Usage Guide](Usage-Guide) for more on patterns.
- **Check your `.paleaeignore`**: You may have a pattern (e.g., `src/`) that is excluding everything. See the [Configuration](Configuration) guide.
- **Check file sizes**: Files over 10MB are skipped by default.

## "Invalid regex"

This error means the pattern you provided to `--include` or `--exclude` is not a valid regular expression.

- **Remember to escape special characters**: For example, to match a literal dot, you must use `\.`. The [Configuration](Configuration) guide has a section on regex patterns.
- **Example**: To match all Python files, use `\.py$` not `*.py`. The latter is a glob pattern, not a regex.

## Out of Memory Errors

If Paleae crashes on a large repository, you are likely running out of RAM.

- **Use JSONL format**: This streams the output and uses significantly less memory, as explained in the [Output Format](Output-Format) guide.
  ```bash
  python paleae.py -f jsonl -o my_snapshot.jsonl
  ```
- **Be more selective**: Use filters to reduce the number of files included in the snapshot.

## `.paleaeignore` Not Working

- **Check the file location**: It must be in the same directory where you are running the `paleae` command.
- **Check the syntax**: `.paleaeignore` uses **glob** patterns (like `.gitignore`), not regex. This is a common mistake. See the [Configuration](Configuration) guide for examples.

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
