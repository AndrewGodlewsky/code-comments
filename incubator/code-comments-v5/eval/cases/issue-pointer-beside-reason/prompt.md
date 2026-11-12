---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Issue #212: the accounting system's nightly import has rejected the whole invoice file twice this week. Their importer checks every amount against `^\d+\.\d{2}$`, so an amount written as 12.5 or 3 fails the entire file. The importer belongs to the finance vendor and we can't change it. Please fix billing/export.py so every amount is written with exactly two decimal places (12.5 becomes "12.50", 3 becomes "3.00").

Input files: billing/__init__.py, billing/export.py
