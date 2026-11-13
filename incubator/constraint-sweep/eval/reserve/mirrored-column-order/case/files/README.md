# bank-bridge

Sends payments to the bank as a CSV export, and reads export files back.

- `payments/model.py`: the payment record.
- `export/columns.py`: the export's columns, in order.
- `export/write.py`: writes the export file (`write_export`).
- `ingest/read.py`, `ingest/layout.json`: read an export file back (`read_export`).
