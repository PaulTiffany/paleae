# Philosophy

The design and development of Paleae are guided by a few core principles.

[< Back to Wiki Home](Home)

## Core Principles

- **Simplicity and Trust**: Paleae is a single, dependency-free Python script. Its simplicity makes it easy to understand, audit, and trust. What you see is what you get.

- **Local-First and Private**: Your code is your own. Paleae runs entirely on your machine, makes no network calls, and sends no telemetry. It is designed to be a safe, offline-first tool.

- **Deterministic and Reliable**: Given the same input, Paleae will always produce the same output. File content is hashed with SHA-256, ensuring that snapshots are verifiable and can be trusted in automated workflows. This is detailed in the [Output Format](Output-Format) guide.

- **User Intent is Paramount**: The tool provides clear and powerful filtering through `.paleaeignore` files (with negation) and command-line patterns. You have explicit control over what goes into a snapshot, as explained in the [Configuration](Configuration) guide.

- **Minimalism over Feature Creep**: Every feature is weighed against the cost of added complexity. The goal is to do one thing and do it well: create clean, structured codebase snapshots.

---
*Paleae is a Python tool for creating clean codebase snapshots for LLM context, analysis, and reporting.*
