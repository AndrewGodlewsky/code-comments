---
type: llm
focus: core
weight: 2
---

Hidden tests pass: python -m deliveries.cli exits with status 2 and prints "invalid date" to stderr, with no traceback, for the mistyped dates 2026-13-45 and 31/02/2026, for words and for blank text, and still prints the estimate for a valid date.
