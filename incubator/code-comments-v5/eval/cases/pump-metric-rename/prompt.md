---
tags: [skill-creator]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

On the ops channel people keep reading pump_runs_total as hours of running time, when it really counts how many times the pumps switched on. Please rename it to pump_starts_total. The Grafana board moved to the new name last week, and the exporter in pumps/ is the only thing in this repo that uses it, so it should be a quick change.
