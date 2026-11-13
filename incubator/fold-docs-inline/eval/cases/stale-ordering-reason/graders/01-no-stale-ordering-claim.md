---
type: llm
focus: core
weight: 1
---

stock_rows gains no comment or docstring line about write_feed, the merge pass or why its rows must be sorted, negated or not; and no other added comment, docstring or document line says that stock_rows() must return sorted rows, that write_feed() needs its rows in SKU order, or that a row out of order is skipped.
