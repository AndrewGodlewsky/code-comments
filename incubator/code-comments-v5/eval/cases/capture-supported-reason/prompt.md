---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Ticket DATA-412: About 3% of customers went missing from last night's warehouse load. The warehouse loader merge-joins each staging batch against the previous snapshot on customer_id in a single pass, so it assumes the batch is sorted by customer_id; rows that arrive out of order are silently skipped. The loader lives in another repository and we can't change it. Please fix this on our side in pipeline/stage.py by making sure each batch is written sorted by customer_id.

Input files: pipeline/__init__.py, pipeline/stage.py
