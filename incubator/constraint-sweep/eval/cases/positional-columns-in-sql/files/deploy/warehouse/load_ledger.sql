-- Nightly load of the CSV that exporter/csv_out.py writes.
-- warehouse-load stages each file as export_staging(c1, c2, ...): fields are
-- numbered by position, and the header row is skipped, not read. The order of
-- COLUMNS in exporter/csv_out.py is therefore part of this contract: new export
-- columns go at the end, or every field after the new one loads into the wrong
-- column here.
INSERT INTO ledger_raw (entry_id, account_code, amount, posted_at)
SELECT c1, c2, c3, c4
FROM export_staging;
