## Review of auth-01 (junior-v3, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added the shared-middleware rule so the protected check and what the route does with the user ID are stated in the file (Q1).
- Set last_seen_at and absolute_expires_at explicitly at login in choice 8, and noted in the schema comments that neither has a default (Q2).
- Defined what counts as a failed attempt in choice 7, and what an empty or over-long email gets (Q3).
- Stated that cleanup runs as a timer inside each app instance and why two instances running it at once is harmless (Q4).
- Added the cookie-lifetime rule about browser close and server rows (Q5).
- Added the storage-failure table and the statement that the app does not retry; the user reloads (Q6).
- Stated that GET /login shows the form and that a POST with a valid cookie rotates the session without redirecting (Q7).
- Fixed failure counting for a first-time email: insert the failure row if missing before SELECT FOR UPDATE, since there is no row to lock otherwise (found while answering Q3 and Q4).
- Changed the 429 Retry-After from a fixed 900 to the seconds left on the lock, because the lock is set at a varying time.
- Merged duplicated lockout, logout and session-state text into one rule each, and moved the storage-failure rules into one table.
- Moved the lockout statement that was repeated under Decision 6 and the diagram into a single rule. Kept the diagram's structure and the four rejection cases.
- Moved the open tradeoffs to the end under Open questions and shortened each to one line.
- Changed: Protected check rule and the diagram note now exclude /logout as well as /login, because logout is a POST that must behave the same with or without a session (Q8).
- Changed: Added a rule that logout is not behind the check, stating that an expired session gets the normal logout reply (Q8).
- Changed: Protected check rule now says the route handler does not run when the middleware returns 503 (Q9).
- Changed: Added a rule and a table row for a route that fails loading its data after the check passed: the app's existing error page is shown and the session stays valid (Q9).
- Restructured the document into the newcomer layout: summary, terms, main flow diagram, decisions and rules, storage-failure table, open questions. Each step now stands alone.
- Merged the 'Choices' list and the 'Rules that do not fit on the arrows' list into one numbered 'Design decisions and rules' list, so each mechanism is stated once.
- Removed the cross-reference 'choice 4' from the shared check rule and replaced it with a reference to the expiry check step, which states the statement itself.
- Merged the 'Session states' rule into the expiry check step, since zero rows already covers idle-expired, absolute-expired, deleted and unknown sessions.
- Merged the 'Cookie lifetime' rule into the cookie decision, and the 'Login always rotates' rule into the login success step.
- Merged the 'Logout is not behind the check' rule into the logout step, which already states the same-reply behavior.
- Merged the 'Route errors after the check' rule into the storage-failure table, which already covers that row.
- Moved the schema below the decisions list, and kept its SQL comments unchanged.
- Defined 'normalized email' as a term, since several steps depend on it.
- Trimmed repeated wording in the lockout, failure counting and cleanup steps without changing their rules, limits or timings.
- Kept the sequence diagram unchanged, including all its alternative branches.
- Kept the storage-failure table content unchanged, since every row reflects a stated requirement, and kept the open questions unchanged. No behavior, limit or timing was changed.

### Holes
- None.
