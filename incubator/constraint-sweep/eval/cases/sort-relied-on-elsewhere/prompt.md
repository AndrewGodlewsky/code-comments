---
tags: [skill-creator]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

fetch_rows is slow on big ledgers, and profiling points at the Python sort at the end of it. It only has two callers, the nightly export and the balances API, and neither cares about order: the accounts team sorts the export themselves, and the API just adds the rows up. Please just drop the sort.
