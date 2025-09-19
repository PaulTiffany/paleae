# Welcome to the Paleae Wiki

Paleae is a single-file, zero-dependency Python tool that creates structured JSON/JSONL snapshots of your codebase. It is the ideal tool to prepare a codebase for analysis by Large Language Models (LLMs), manage LLM context windows, or for any task that requires a clean, machine-readable representation of your code.

This wiki provides comprehensive documentation for Paleae's features, configuration, and use cases, helping you create the perfect Python code snapshot.

## Quick Navigation

- [Getting Started](Getting-Started) - Installation and your first snapshot.
- [Cookbook](Cookbook) - Practical recipes and examples.
- [Usage Guide](Usage-Guide) - All command-line options and examples.
- [Configuration](Configuration) - Using `.paleaeignore` and profiles to customize your snapshot.
- [Output Format](Output-Format) - A detailed look at the JSON/JSONL structure.
- [Philosophy](Philosophy) - The design principles and vision behind the project.
- [API Reference](API-Reference) - For programmatic usage.

---

## Key Features

- **Single File, Zero Dependencies**: `paleae.py` is a self-contained script. Drop it into any project and run it with a standard Python 3 interpreter.
- **Local-First and Private**: Paleae runs entirely on your machine. It makes no network calls and sends no telemetry. Your code remains private, always.
- **AI-Optimized Output**: The output is clean, structured JSON or JSONL, designed for easy parsing by AI models.
- **Powerful Filtering**: Customize your snapshots with a `.paleaeignore` file that uses familiar `.gitignore` syntax, including negations (`!`).
- **Reliable and Deterministic**: With a comprehensive test suite, Paleae provides predictable, deterministic output.

---

## Quick Example

Run Paleae in your project directory:
```bash
# Download the script
curl -fsSL https://raw.githubusercontent.com/PaulTiffany/paleae/main/paleae.py -o paleae.py

# Run it
python3 paleae.py
```

This creates a `repo_snapshot.json` file that looks like this (simplified):
```json
{
  "meta": {
    "tool": "paleae",
    "version": "1.0.0",
    "summary": {
      "total_files": 5,
      "estimated_tokens": 2560
    }
  },
  "files": [
    {
      "path": "src/main.py",
      "content": "def hello():\n    print(\"Hello, World!\")\n",
      "sha256": "..."
    }
  ]
}
```

## Support

- Report bugs and request features on [GitHub Issues](https://github.com/PaulTiffany/paleae/issues).
- Ask questions and share ideas in [GitHub Discussions](https://github.com/PaulTiffany/paleae/discussions).

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
