---
tags: [skill-creator]
max_turns: 25
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash]
---

Our other command line tools all call this option --after, so please rename the export command's --since option to --after to match. It should behave exactly as it does now. Only our own jobs call reportctl, so there's no need to keep the old spelling.
