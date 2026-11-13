## Review of auth-03 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a two-to-three sentence summary (how the system works today, the main flow, and why it is shaped this way) and a Terms list before the diagram: token, password_reset_tokens columns, consumed/superseded, sessions, email queue/worker, breached-password list.
- Moved the Stores block out of the diagram header into the terms and the Data note, so the schema is stated once.
- Replaced the Data, Concurrency and Link checks notes with a Rules list (the brief's fixed requirements at the step each applies to) and a short Why it is shaped this way section. Merged duplicated statements of one-row-per-email, rows kept at least 1 hour, cleanup after a day, and the check-twice behaviour.
- Kept the three diagram sections unchanged, since they are the flow.
- Merged the Security details into one shorter Security list, with the Referrer-Policy and hash-lookup points kept once each.
- Kept the failure table; trimmed the mail-failure row by moving the 'known gap, worker unchanged, add an alert' wording to Open questions.
- Added a 'Rules' line for the 12-character minimum, breached-list rule, retry-until-expiry, logout on every device, and no auto-login, so every fixed requirement appears in one place.
- No questions were supplied, so no step-specific answers were added beyond the terms. Nothing from the first version was dropped.

### Holes
- None.
