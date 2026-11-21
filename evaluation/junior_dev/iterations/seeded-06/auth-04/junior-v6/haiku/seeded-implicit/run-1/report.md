## Review of auth-04 (junior-v6, author haiku, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Rewrote the document for a newcomer: summary first, then terms, then the Mermaid flowchart with notes, then numbered steps, a state table, a failure list, build notes and open questions.
- Defined the Redis start entry (key, fields, 10-minute TTL, read-and-delete on callback) and the pending link entry with its cookie and removal rules.
- Added the user_identities table with its primary key and UNIQUE constraints, and the users.password_hash change to nullable.
- Added the PKCE challenge, the scopes, the ID token checks and the code-exchange failure handling.
- Split the callback into login mode and link mode, with the sid check and the already-linked and other-link refusals for link mode.
- Added the refusals for an unverified email, a matched account with no password, and a Google account already linked to someone else.
- Wrote the confirm-password loop: the lock check, the wrong-password count, lock deleting the pending link, and the duplicate-link refusal on success.
- Added the unlink rule (only with a password, otherwise the reset email) as step 9.
- Added failure outcomes for Google denial, bad state, failed exchange, Google slow, Redis down, and sid mismatch.
- Decided that Google sign-in does not check locked_until, and that /login treats a NULL password_hash as a wrong password without changing lockout fields.
- Kept every stated requirement from the brief and the first version; no requirement was cut.
- Pending link now stores next, so the confirm step can redirect after success (Q9).
- Confirm step states how the pending ID cookie is tied to the browser, that a new pending link replaces it, and that the newest one is used (Q10).
- Fifth wrong password now deletes the pending link and sends the user to the login page with Account temporarily locked. The failure table says a new Google start gets a confirm page but the password is not checked while locked (Q11).
- Step 2 and the start step now name the return page and say the Google error reply carries the same state, so the saved return page is found (Q14).
- Step 8 now says start_session replaces an old session of another user, as password login does today (Q12).
- Build notes now say a Google-created user can only get a password through the reset email, and cannot unlink until they have one (Q13).
- Terms now define mode, return page, next and the pending ID cookie. The flow diagram adds next to the start entry and the pending link, a no-pending-link check at confirm, and the login-page destinations for lockout and refusal.
- The failure table is now one table. It adds Redis-unavailable at confirm, the fifth-miss case, and the Google-only user on /login.
- Notes now say the lock check applies only at confirm, and that refusals show a message on the return page.
- Reordered to the skill's layout: summary, terms, diagram with notes, numbered steps, where state lives, failure table, build and rollout notes (kept apart from how the system runs), open questions.
- Summary: kept how POST /login works today (bcrypt, 5 misses, 15-minute lock, start_session) and the three-part flow; added why accounts match by sub and why an existing account is linked only after its password (so email alone cannot take over an account).
- Terms: defined sid cookie and sessions row, relative path, S256 challenge, lockout fields, and the pending ID cookie; each term is one plain line.
- Steps: each step now states what starts it, what it does, where its data lives, and what happens on failure. Merged the repeated 'Redis unavailable' and 'change nothing' wording into each step.
- Added from the junior's answers: the pending ID cookie is HttpOnly, Secure and SameSite=Lax, and only the browser that finished the round trip holds it (A10); a locked user who restarts Google gets a confirm page and the lock is checked only at submit (A11); the return page and next are read from the state entry before it is deleted (A9, A14).
- Added from the junior's answers: the start step saves the return page and the callback reads it from the entry before deleting it (A14). Google's error reply carrying the same state is stated as an OAuth 2.0 standard (RFC 6749); the repository does not show this, so it is an unverified claim.
- Diagram: same nodes and branches as the first version, with the labels kept in plain words. No branch was added or removed.
- Kept every stated fact from the brief and the first version, checked line by line: the 10-minute round trip, single-use callbacks, Cancel handling, sub-only matching, one link each way, unverified-email refusal, the password-confirmation loop and lockout, the settings link and unlink rules, the same session for every sign-in, the state-table, all 14 failure rows, the build notes and all five open questions.
- Build notes: moved the Google-only user rule (cannot unlink until a password exists) next to the reset-email rule, so it reads as one rule.
- Not changed: the design itself. No new mechanism, lock, retry or takeover rule was added. Only the questions' answers already in the junior's file were used.
- Not done: no teach-back run. This rewrite has not been checked by a fresh junior.

### Holes
- None.
