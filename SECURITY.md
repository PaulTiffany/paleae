# Security Policy

Paleae is a **single-file, local-first snapshot tool** with **no network access** and **no runtime dependencies**. 
The attack surface is intentionally small, but we still welcome responsible disclosure.

---

## Supported Versions

We accept security reports for:
- The latest release tag on GitHub
- The `main` branch (HEAD) as published in this repository

Older releases are generally unsupported unless the issue is severe and broadly impactful.

---

## Reporting a Vulnerability

**Preferred:** Use GitHub’s **Private Vulnerability Reporting** (Security → “Report a vulnerability”) on this repo.  
**Fallback:** Email **<paulctiffany@gmail.com>** with the details.

*Note: While email is provided as a fallback, we strongly prefer using GitHub's Private Vulnerability Reporting for enhanced security and tracking. For future consideration, a dedicated security email alias (e.g., `security@yourdomain.com`) is recommended to manage reports and reduce spam.*

Please include:
- Clear reproduction steps (commands, flags, input files if possible)
- Impact and likelihood
- A minimal proof-of-concept (no destructive payloads)
- Your preferred credit name/handle

We aim to acknowledge within **48 hours** and provide a remediation plan or fix within **7–14 days** for high-severity issues.

---

## Coordinated Disclosure

We follow coordinated disclosure:
1. We confirm and triage the report.
2. We prepare a fix and security advisory.
3. We publish a new release and advisory notes.
4. We credit reporters who request attribution.

If your report reveals active exploitation or widespread risk, we may accelerate timelines and/or release a temporary mitigation.

---

## In Scope

Because Paleae is a local CLI that **reads files and writes snapshots**:
- Path traversal or file read beyond the selected scope (e.g., bypassing includes/excludes/.paleaeignore)
- Determinism or hashing flaws that could **silently** corrupt or misrepresent snapshot contents
- Logic that causes **unexpected network activity** (none should exist)
- Unsanitized execution of external inputs (none should exist)
- Resource exhaustion that leads to **unbounded memory/CPU** usage despite caps

---

## Out of Scope

- General usability issues, performance tuning, or feature requests (please open a normal issue/PR)
- Impacts that require users to ignore documented flags, bypass `.paleaeignore`, or modify the code
- Scenarios that rely on malicious modification of the Paleae script **after** download (supply chain is handled by release integrity below)

---

## Handling Sensitive Data in Snapshots

Paleae intentionally **does not upload or transmit** data. Users are responsible for:
- Adding patterns to `.paleaeignore` (supports `!negation` to re-include)
- Verifying output before sharing snapshots publicly

If your report concerns accidental capture of secrets with default profiles, include a minimal example and we will consider safer defaults.

---

## Release Integrity & Verification

To reduce supply-chain risk:
- Always download from the official GitHub releases or repo.
- Verify the **SHA-256** of `paleae.py` against the value posted in the release notes (when provided).
- Avoid third-party mirrors.

---

## Development & Dependencies

- Single file, Python standard library only (no runtime dependencies).
- No telemetry; no auto-update; no network calls.
- Deterministic traversal and hashing intended for reproducibility.

If you discover behavior that contradicts the above guarantees, please report it as a security issue.

---

## Responsible Research

We appreciate good-faith testing that avoids disrupting others. Please do not publicly disclose details before a fix is available. 
We are happy to discuss embargo timing if needed.

---

## Contact & Keys

- Security contact: **<paulctiffany@gmail.com>**
- PGP key (optional): publish a fingerprint here if you require encrypted reports.
