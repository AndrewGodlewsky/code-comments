---
tags: [skill-creator]
max_turns: 20
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

Please rename compute_total to invoice_total across the billing package. The new tax module has its own compute_total and having two is confusing.

Input files: billing/__init__.py, billing/totals.py, billing/invoice.py, billing/discounts.py, docs/billing.md, tests/__init__.py, tests/test_totals.py
