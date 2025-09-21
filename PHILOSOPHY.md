# Philosophy

Paleae embodies a simple conviction: **good tools should be predictable, transparent, and trustworthy**.

This document outlines the core principles of the project. For detailed usage and configuration, please see the [Paleae Wiki](paleae.wiki/Home.md).

## Core Principles

### Single File, Zero Dependencies

One file. One purpose. No hidden complexity.

When you download `paleae.py`, you get the entire tool. No package managers, no dependency trees, no version conflicts. You can read every line of code, understand exactly what it does, and trust that it will work the same way tomorrow as it does today.

This isn't a limitation—it's a feature. Constraints breed clarity.

### Local-First

Your code never leaves your machine during scanning. No network calls, no telemetry, no "phone home" behavior. Paleae runs where you run it, processes what you tell it to process, and writes output where you specify.

In an era of cloud-everything and data collection, this is a deliberate choice. Your repositories contain your ideas, your competitive advantages, your mistakes, and your breakthroughs. They shouldn't require an internet connection to analyze.

### Predictable by Design

Paleae produces deterministic output. The same codebase scanned twice will generate identical snapshots (modulo timestamps). File traversal follows consistent patterns. Error messages are clear and actionable.

Surprises are bugs, not features.

### Lean but Powerful

Every feature must justify its existence. Every line of code must serve a purpose. We resist feature creep not out of laziness, but out of respect for the core mission.

The goal isn't to build the most feature-rich repository scanner. The goal is to build the most trustworthy one.

## Design Decisions

### Why JSON/JSONL?

Structured data beats clever formatting. JSON is universal, parseable, and future-proof. JSONL handles large repositories gracefully and streams naturally. Both formats work everywhere, with everything.

Human-readable is important, but machine-parseable is essential. See the [Output Format](paleae.wiki/Output-Format.md) guide for details.

### Why Regex Patterns Instead of Globs?

Power users need precision. While `.paleaeignore` uses familiar glob syntax, the CLI accepts regex patterns for maximum flexibility. This dual approach serves both casual users and power users without compromise. This is explained in the [Configuration](paleae.wiki/Configuration.md) guide.

### Why SHA-256 Hashes?

Trust requires verification. Every file in the snapshot includes its SHA-256 hash, enabling you to verify the integrity of the data and detect changes over time. This isn't paranoia—it's engineering rigor.

### Why No Configuration Files?

Configuration files create state. State creates complexity. Complexity breaks predictability.

Paleae takes its instructions from [command-line arguments](paleae.wiki/Usage-Guide.md) and [`.paleaeignore` files](paleae.wiki/Configuration.md) that live alongside your code. Everything else is convention and sensible defaults.

## What Paleae Is Not

- **Not a code analysis tool.** It snapshots, it doesn't analyze.
- **Not a backup solution.** It captures text content, not complete repository state.
- **Not a deployment tool.** It creates data for other systems to consume.
- **Not a cloud service.** It's a local utility that respects local control.

## The Grain Metaphor

"Paleae" refers to the chaff that surrounds grain—the protective husks that must be separated to reveal the valuable core.

A codebase is the same. It contains signal (source code, key configurations) and noise (build artifacts, logs, binaries). For a Large Language Model, this noise is detrimental. It consumes precious context window space, introduces irrelevant information, and degrades the quality of analysis.

Paleae is the winnowing fan for your code. It helps you separate the grain from the chaff, creating clean, dense, signal-rich snapshots that are perfectly optimized for AI consumption. Like traditional winnowing, this process requires judgment. That's why Paleae gives you precise [filtering control](paleae.wiki/Configuration.md) over what gets included and what gets filtered out.

## Long-term Thinking

Software tools often grow until they collapse under their own weight. Paleae chooses a different path: **sustainable minimalism**.

We will:
- Resist feature requests that compromise core principles
- Maintain backward compatibility aggressively
- Keep the single-file constraint inviolate
- Prioritize reliability over novelty

The best tools become invisible infrastructure. They work so consistently that you stop thinking about them and focus on your actual work instead.

That's the goal.
