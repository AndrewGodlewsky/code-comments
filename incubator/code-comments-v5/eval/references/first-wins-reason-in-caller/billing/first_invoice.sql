-- Accounts whose trial has ended and that have not been invoiced yet.
CREATE VIEW due_for_first_invoice AS
SELECT trial_clock.user
FROM trial_clock
LEFT JOIN invoices ON invoices.user = trial_clock.user
WHERE trial_clock.trial_ends <= datetime('now') AND invoices.user IS NULL;
