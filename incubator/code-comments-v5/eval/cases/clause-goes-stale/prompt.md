---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Make parse_tags return an empty list when text is None instead of raising. It should still raise for text that has no tags in it.

Input files: tags/__init__.py, tags/parse.py, tags/search.py, tests/__init__.py, tests/test_parse.py
