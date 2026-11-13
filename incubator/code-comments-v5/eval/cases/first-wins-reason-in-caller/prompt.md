---
tags: [skill-creator]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

one_login_per_user in accounts/events.py is clunky. Please simplify it. I don't think it matters which of a user's logins it keeps, as long as there is one per user, so a one-liner like last_devices in accounts/devices.py would be fine.
