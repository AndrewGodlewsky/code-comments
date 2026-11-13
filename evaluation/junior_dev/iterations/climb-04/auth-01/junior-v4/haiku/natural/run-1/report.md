## Review of auth-01 (junior-v4, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added a CSRF check step to login and logout in the diagram, and defined the `__Host-csrf` token cookie (answers Q1).
- Stated that a login deletes only the session matching this browser's cookie, and that other devices stay valid (Q2).
- Added the 429 message and how Retry-After is computed, and that a lock does not end existing sessions (Q3).
- Stated in the notes that the 5th failure gets the identical 401, and that the user learns of the lock on the next attempt (Q4).
- Added a lock-timeout row to the failure table: it is a database error, rolled back, with 503 and nothing counted (Q5).
- Stated that the user_id from the check is attached to the request, and that one shared check guards every route except /login (Q6).
- Added the bcrypt cost factor and login duration as an open question, since the plan does not set them (Q7).
- Corrected the clearing cookie: Max-Age=0 is used when clearing, and the 'no Max-Age' rule now applies only to the issued cookie (Q8).
- Rewrote the file in the newcomer layout: summary, terms, choices, sequence, notes, failures table, constants, rollout, open questions.
- Removed the decision-number references, the duplicate session-fixation decision, and the separate residual-risks heading, merging them into the choices and rollout sections.
- Added an email length rule (254 characters, same 401, no row written) and a cleanup failure row to the failure table.
- Moved the stated rules into the notes, so the diagram keeps the flow and the notes keep the rules that do not fit on the arrows.
- Added open questions about the second cookie versus the brief's single-cookie rule, browser session restore, and local HTTPS.
- Reordered the document into the newcomer layout: summary (with how the app works today), terms, design choices, numbered steps, sequence diagram, notes, failures table, limits, build and rollout, open questions.
- Merged the three places that explained cookies (terms, choices, notes) into one cookie note; merged the session-ID definition and its hashing rationale into one term and one choice.
- Rewrote the failure-count explanation (previously in both a lifecycle note and the diagram notes) as one failure-rules bullet.
- Moved the cleanup rules from their own section into numbered step 4, so the cleanup job has the same four parts as the other steps.
- Merged the email-length note into step 1 and the logout-idempotence note into step 3.
- Merged the 'locks and existing sessions' and 'other devices' notes into one bullet.
- Removed diagram notes that repeated the notes below the diagram; the diagram flows and their arrows are unchanged.
- Moved storage-swap, load-testing and targeted-lockout items into a separate 'Build and rollout' section, apart from how the system runs; removed the local-development item from that section because it already appears as an open question.
- Added one sentence stating that unknown emails also get failure rows, so the 429 does not reveal whether an account exists. The diagram already implies this, so no behaviour changed.
- Kept all four open questions and all behaviour, constants and failure responses unchanged.

### Holes
- Q7: The 'Unknown email or wrong password' branch updates login_failures after a bcrypt check. If the transaction holds the row lock during bcrypt, how long does a login attempt take and what do concurrent attempts for different emails do? (author: Concurrency for different emails is clear from the design: each email has its own row lock, so attempts for different emails do not block each other. They do share the database connection pool, so the bcrypt time limits how many logins run at once. How long one attempt takes depends on the bcrypt cost factor, which the plan does not set. That is listed as an open question and needs a load test.)
