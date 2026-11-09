---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Implementing #318: add a --limit N option to the tasks command so it prints at most the first N tasks it would otherwise show. Without --limit it should behave exactly as before.

Input files: tasks/__init__.py, tasks/cli.py
