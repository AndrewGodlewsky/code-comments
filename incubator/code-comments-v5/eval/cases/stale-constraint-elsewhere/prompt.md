---
tags: [skill-creator]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

load_readings is slow on the big gateway files, and profiling points at the sort inside it. Please take that sort out.
