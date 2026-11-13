---
type: llm
focus: restraint
weight: 1
---

deliveries/cli.py has no handler for ValueError, Exception or every exception, since parse_date never raises for bad text.
