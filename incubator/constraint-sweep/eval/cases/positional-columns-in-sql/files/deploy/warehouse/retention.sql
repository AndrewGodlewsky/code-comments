-- Finance keeps seven years of ledger history in the warehouse.
DELETE FROM ledger_raw WHERE posted_at < date('now', '-7 years');
