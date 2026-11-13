---
tags: [skill-creator]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

parse_date returns None when it's given something that isn't a valid date (its docstring says so). Please make the deliveries CLI check for that: when it gets None back, it should print "invalid date" to stderr and exit with status 2, so a mistyped date gets a clear error message.
