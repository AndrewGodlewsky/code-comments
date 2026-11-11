---
type: llm
focus: core
weight: 1
---

BATCH_SIZE is 250, so the 250th notification sends a batch and the 249th does not, while the flush interval is still 30 seconds (hidden tests).
