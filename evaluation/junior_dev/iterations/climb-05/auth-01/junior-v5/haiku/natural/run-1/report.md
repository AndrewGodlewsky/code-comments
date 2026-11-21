## Review of auth-01 (junior-v5, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Summary: rewritten to say what the app is, how it works today (all pages public), and how sign-in works in one paragraph; choices are now a short list in the summary, so the separate numbered Choices section is gone.
- Added a terms section defining app, session, session ID, Redis, TTL, idle and absolute expiry, failure count, lock, hash, fail closed and key names.
- Login success path: the three Redis writes are now one MULTI/EXEC transaction, so a partial failure cannot leave a half-done login (Q1).
- Session record: holds only user_id, created_at and absolute_expires_at; protected-page checks read only Redis, with no Postgres read per request (Q2).
- Protected-page step 5: explains that the 12-hour cap is enforced by the time-left TTL, which applies after 11.5 hours, with a worked example (Q3).
- Login step 6: states that the Lua script returns only a count, the app returns 401 for the failed attempt, and the lock is seen on the next attempt as 429 (Q4).
- Protected page: any Redis error at GET, EXPIRE or the expiry DEL returns 503 with the cookie kept (Q5).
- Logout: added the 503 branch for a failed DEL, a rule that a missing key counts as success, and that logout needs no valid session (Q7). Sequence diagram updated to match.
- Added a failure table covering login lock check, user read, transaction, Lua script, protected page and logout (Q1, Q5, Q6, Q7).
- Replaced the 'brief' wording with 'requirements' throughout (Q8).
- Merged the rules list: duplicate login and session statements were combined; the dummy-hash timing rule moved into the choices list.
- Moved the Postgres session-store fallback out of the choices and into a separate build-and-rollout section, so how the system runs is kept apart from how it is rolled out.
- Open questions gathered at the end in one list; the reviewer's identity is marked as not stated in the requirements.
- Sequence diagram: added error branches for Redis and Postgres failures on login, the transaction result, the protected-page GET and the logout DEL; labelled the Lua step with the lock and fails effects; the request-for-protected-page and logout alternatives now match the failure table.
- Login step 2: replaced the EXISTS check with one PTTL call, explained the -2 and milliseconds replies, and stated that Retry-After is the remaining time rounded up to whole seconds, with the reason (no second call, no race).
- Terms: added PTTL, defined in one line with its -2 reply.
- Diagram: the lock check is now PTTL, with the -2 (not locked) and milliseconds-left (locked) replies, and the 429 note names the Retry-After source.
- Failure table: the Login step 2 row now names the PTTL lock check.
- Summary: merged the two summary paragraphs into one short paragraph that first says how the app works today (public pages, no sign-in). Moved the design choices into one list directly after it, each as one line, with the explanation of why Redis was chosen kept in one clause.
- Terms: expanded from 13 to about 22 one-line definitions. Added terms a newcomer needs: Postgres and the users table, bcrypt, dummy hash, cookie, key, PTTL, Lua script, MULTI/EXEC, sorted set (in Failure count), session fixation, Retry-After. Removed the standalone 'Key names' line and folded the three key kinds into the Key term.
- Diagram: kept the same sequence and labels, and moved it to sit after the summary and terms, with its notes directly after it, as the layout rule requires. Removed the double quotes from the 401 label and the '#' and ';' characters Mermaid would misread (none were used in the diagram itself).
- Notes after the diagram: kept only the notes that do not fit on arrows. Merged the per-email key rule, the Redis-only session check, GET /login, redirect codes, UTC clocks and the success-clears-count rule into one list.
- Login steps: rewrote each step to stand alone with what starts it, what it does, which data it keeps and what happens on failure. Added the answers' clarifications in place: the PTTL single call gives both lock state and Retry-After (step 2); the lock check runs before the user read and the user read before any password check (steps 2 and 3); the transaction covers the old session, new session and failure-count clear (step 5); the Lua script returns only the count, the app does not read the lock after it, and the next attempt gets 429 (step 6).
- Protected-page steps: added the 12-hour mechanism as a plain explanation in step 5 (before 11.5 hours a full 30-minute TTL, after that the TTL shrinks). Stated in each step that a Redis error at any point returns 503 with the cookie kept. Removed the repeated 'Redis is not read' detail where it was already covered by step 2.
- Logout: rewrote as three steps. Logout needs no valid session. A failed DEL returns 503 and keeps the cookie, and success returns 303 with the cookie cleared. Stated the reason in one clause.
- Failure table: kept the same rows and outcomes, shortened the wording, and kept the step numbers within each section only. No codes such as R3 or Q7 remain.
- Build and rollout: moved to its own section, separate from how the system runs. Kept Redis replication, HTTPS for local development and the Postgres fallback, unchanged in substance.
- Open questions: kept all seven, unchanged in substance, and placed them at the end. Each one still says why it is open. The Login CSRF and Lockout items keep the requirement-based wording and the reason they are not in the design.
- Cut: repeated statements of the same rule (the lock rule appeared in the summary, steps, rules and table), the 'Rules' section (its items were moved into the steps or the notes), and the duplicated statement that the 401 is returned whatever the count (kept once in step 6). The design itself is not changed: all the requirement decisions and the answers already recorded in the document are kept.

### Holes
- None.
