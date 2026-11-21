## Review of dp-01 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary at the top, placed before the terms, in place of the first version's opening design text.
- Added a terms section defining each name a newcomer would not know: replica, warehouse, watermark, lookback, run_id, staging table, MERGE, lock, COMMIT/ROLLBACK, shadow table, creation day, checksum, deadline and on-call.
- Defined run_id as one ID per attempt. The first version used one staging table per attempt named by run_id and checked whether a run_id committed before a retry, which only works with a per-attempt ID. This clarifies the plan and does not change its behavior.
- Merged the 'what starts each step', 'data movement', 'merge logic' and nightly 'failure and retry' sections into nine numbered steps. Each step says what starts it, what it does, which data it touches and what happens on failure. The first version's repeated staging and retry statements now each appear once.
- Corrected the lock release: a failed attempt releases the lock only if it holds it. The flowchart's failure node released the lock even after 'lock held by another run', which would have released another run's lock. Changed the flowchart label to match; no other flowchart node changed.
- Stated that an attempt still running at its deadline is stopped and counts as failed. The first version implied this only through the deadline sentence.
- Moved dashboards, the watchdog and reconciliation into their own section, because they run on other schedules. Reconciliation's reload and recheck rules are unchanged.
- Replaced the first version's separate failure text with one failure table. Added rows for the deadline, the third attempt, the 06:00 staleness case, the reconciliation alert and reconciliation waiting for an uncommitted night.
- Moved the assumptions and the version tie-break point into open questions, with one line each. Added open questions for the first-run watermark, a stale lock with no release rule, and the third-attempt COMMIT check. None of these was answered in the plan, so none was guessed.
- Cut repeated rules and the separate 'what starts each step' list. Kept every number, setting and rule from the brief and the first version: 02:00 start, read-only replica, 2-hour lookback, 90-minute bulk imports, 15-minute retries, three attempts, 06:00 dashboards and watchdog, #data-alerts, Sunday reconciliation over 30 creation days, 64-bit hash, UTC ISO-8601 timestamps, reload in its own transaction, and the shadow-table fallback.
- Did not add any new mechanism. No lock lease, takeover rule or retry queue was added, because the brief does not require one.

### Holes
- None.
