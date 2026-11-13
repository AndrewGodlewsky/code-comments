---
type: llm
focus: preservation
weight: 1
---

Every comment line in deploy/warehouse/schema.sql is kept. Every comment line in deploy/warehouse/load_ledger.sql is kept, or, if its SQL changed, its comments still say that the fields are read by position from the COLUMNS in exporter/csv_out.py.
