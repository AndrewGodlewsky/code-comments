---
type: llm
weight: 1
---

pipeline/stage.py records why the batch must be sorted: the warehouse loader merge-joins on customer_id and skips rows that arrive out of order.
