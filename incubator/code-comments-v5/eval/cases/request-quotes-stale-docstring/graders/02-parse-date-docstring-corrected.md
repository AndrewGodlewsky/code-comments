---
type: llm
focus: core
weight: 1
---

parse_date's docstring no longer says, unqualified, that it returns None for text that is not a valid date: it drops that claim, or it also says that parse_date raises ValueError for a date that does not exist.
