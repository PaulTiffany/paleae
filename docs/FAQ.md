# Paleae Frequently Asked Questions (FAQ)

Common questions and answers about using Paleae to create Python code snapshots for AI analysis and LLM context management.

## General

### What is Paleae used for?
Paleae is a single-file, zero-dependency Python tool that creates structured JSON or JSONL snapshots of a codebase. Its main use is to prepare code for analysis by Large Language Models (LLMs) by creating a clean, context-rich representation of a repository.

### How is Paleae different from `zip` or `tar`?
While tools like `zip` just archive files, Paleae is designed to intelligently prepare your code for analysis. It filters out irrelevant files, includes essential metadata, and produces a clean, machine-readable [JSON or JSONL output](Output-Format) perfect for scripting and AI context windows.

## Installation

### How do I install Paleae?
There is no installation. Paleae is a single Python file. For a complete walkthrough, see the [Getting Started](Getting-Started) guide.

## Usage

### How can I control which files are in the snapshot?
Paleae offers powerful filtering options. You can use a `.paleaeignore` file for project-specific rules or use command-line flags like `--include` and `--exclude` for ad-hoc filtering. Both methods are covered in the [Configuration guide](Configuration).

### What is the difference between JSON and JSONL output?
- **JSON**: A single, human-readable file. Best for smaller projects.
- **JSONL**: A stream of JSON objects, one per line. Best for very large projects as it is more memory-efficient.

See the [Output Format documentation](Output-Format) for a detailed comparison.

### How can I manage the snapshot size for an LLM context window?
The estimated token count in the metadata helps you gauge the size. For practical examples of how to reduce the snapshot size to fit a specific token budget, see the recipes in our [Cookbook](Cookbook).

## Technical

### Why are some of my files missing from the snapshot?
This is usually due to filtering. Paleae skips files that are over 10MB, binary files, or files that match an exclusion pattern. For a full checklist, see the [Troubleshooting guide](Troubleshooting).

### Can I use Paleae as part of a script?
Yes. Paleae can be imported as a standard Python module. The [API Reference](API-Reference) provides complete documentation for programmatic usage.

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
