-- The warehouse table that deploy/warehouse/load_ledger.sql fills each night.
-- Columns are only ever added at the end (ALTER TABLE ... ADD COLUMN).
CREATE TABLE ledger_raw (
    entry_id TEXT NOT NULL,
    account_code TEXT NOT NULL,
    amount TEXT NOT NULL,
    posted_at TEXT NOT NULL
);
