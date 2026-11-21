## Review of auth-03 (rewrite-v7, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a short summary that says how the existing system works today (sessions checked per request, email queue and worker) before describing the change.
- Added a Terms section defining token, hash, session, email queue and burn, the only names a newcomer would not know.
- Kept the original ASCII diagram unchanged, and made the steps add only what the diagram cannot show: what starts each step, what it stores, and the order of checks.
- Replaced the four-line notes with the rules that apply across steps (30 minutes, single use, new link kills old, rate limit counting) and placed each rule once.
- Specified the reset_tokens design needed for the brief: rows keep a hash, expiry and used flag, so the earlier-link kill, single use and rate limit all use one table. Used-flag and single-transaction burn are how two submits cannot both succeed.
- Added the failure table, covering failures the first version did not address: expired or used link on load or submit, rejected password, double submit, database error during submit, and confirmation email failure. Each row uses only behaviour stated in the brief or implied by the single transaction.
- Kept every stated fact from the brief: the exact generic message, the unknown-address behaviour, the 3-per-rolling-hour limit and its effect, 32-byte random token stored as SHA-256 only, 30-minute validity, single use, kill of earlier links, the two-stage token check, the password policy, link staying usable after rejection, hash storage, burning the link, logging out every device including the current one, the change email, the redirect to login and no automatic login, and the queue's 3 retries with backoff then drop.
- Cut the duplicated flow descriptions in the notes, since the diagram and steps now carry them once. Did not add locks, retry queues or takeover rules.
- Added four open questions for points the brief leaves unset: silent drop after failed sends, the raw token sitting in the queue job, cleanup of old rows, and the breached-list source and update schedule.

### Holes
- None.
