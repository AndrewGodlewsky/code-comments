-- Nightly load of the CSV that exporter/csv_out.py writes.
-- warehouse-load stages each file as export_staging(c1, c2, ...): fields are
-- numbered by position, and the header row is skipped, not read. The order of
-- COLUMNS in exporter/csv_out.py is therefore part of this contract: when a column
-- is added or moved there, renumber the SELECT below, or fields load into the wrong
-- columns here. c4 is the currency code, which ledger_raw does not keep.
INSERT INTO ledger_raw (entry_id, account_code, amount, posted_at)
SELECT c1, c2, c3, c5
FROM export_staging;
