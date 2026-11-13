## Review of auth-01 (junior-v7, author haiku, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a summary that says how the system works today and how the flow goes from start to finish.
- Added a Terms section defining session, sid cookie, HttpOnly, Secure, SameSite=Lax, bcrypt, failure row and lock.
- Added a Tables section with the columns of sessions, login_failures and login_locks, which the original only named.
- Specified the login rules: lowercase email, lock check before password check, and the 5-failures-in-10-minutes lock for 15 minutes.
- Added the rule that failures for unknown emails are counted and locked, so a 429 cannot reveal whether an account exists.
- Specified how idle (30 min, reset every request) and absolute (12 h) expiry are stored and checked, using a single query and the Postgres clock.
- Specified the transaction that replaces the incoming session with a new random ID, and the cookie flags.
- Specified logout: delete before replying, same response with or without a session.
- Added a failure table covering locked, bad credentials, DB error or timeout, transaction failure, unknown session, logout error and cleanup error, with fail-closed behavior.
- Specified the cleanup job: 10-minute interval, runs in the app on both instances, and what it deletes.
- Added Design choices stating Postgres over Redis or process memory, per-email lockout, session IDs, leaving other sessions alone, and fail-closed storage behavior.
- Added open questions for per-email lockout abuse, the race that lets a few extra guesses through, and unhashed session IDs.
- Expanded the diagram's notes into labelled steps. The diagram itself keeps its original flows and adds the locked and session-found branches.
- Summary now says how today's public pages work and walks the main flow from start to finish, with the reason for Postgres.
- Added one-line terms for instance, load balancer, Postgres, Postgres clock, dummy hash, idle and absolute timeouts, failure row, lock, cleanup job, and the cookie flags.
- Moved the stored tables ahead of the diagram, with the terms, so the diagram keeps its form and the steps follow it.
- Fixed the protected-page step: it now runs for every request, including one with no sid cookie, which the brief requires (requirement 7).
- Login step 3: stated that a failed transaction leaves the old session in place. Login step 4: stated that the fifth failure gets 401 and the next attempt gets 429, and gave the one-clause reason for counting unknown emails.
- Logout step 2: stated that the session is already deleted when the reply is sent.
- Added a failure-table row for a database error while writing a failure row or lock, which the first version did not cover. The failed attempt may not be counted; this is noted, not solved.
- Merged the separate idle-timeout and cleanup paragraphs into the protected-page step and the cleanup step. Merged the unknown-email lock note into login step 4.
- Moved the design choices into one Choices list, each with its reason, and kept the reasons that a step needs next to that step. Recorded that the 5-second reply limit is my choice and that the brief sets none, and that other devices keep their sessions.
- Kept every brief requirement, every number and message, every first-version rule, the diagram, and the three open questions. The junior's round-1 answers Q1 to Q8 are all covered in the file.
- Step 3 (login): added that a missing or unknown sid cookie makes the delete remove nothing and login continues. Reason: Q10.
- Step 4 (login): now one transaction that inserts the failure row, counts the last 10 minutes, and upserts the lock, so an expired lock row is replaced. Reason: Q14, the first version did not say how the count or an existing lock row is handled.
- Step 2 (protected page): stated that being signed in is the only check and that there are no roles. Reason: Q11.
- Step 3 (protected page): stated that the user does not return to the requested page and goes to /dashboard after sign-in. Reason: Q12.
- Choices: added that login reads no IP or other identity, so attempts are told apart by the lowercased email. Reason: Q9.
- Choices: the 5-second limit is now stated as one limit for the whole request. Reason: Q13.
- Added a paragraph under the failure table on what happens when a database reply arrives after the 503 was sent. Reason: Q13.
- Summary: added one sentence on how the app works today (no sign-in, all pages public). Reason: the layout rule requires the current system first.
- Terms: added Upsert and Fail closed, which the new step wording uses. Reason: a newcomer would not know these terms.
- Layout: moved the diagram after the terms and added a short rules section after it, per the diagram layout rule. Stored data moved under the terms.
- Open questions: added a line that user creation and password setting are not covered by this plan. Reason: Q15.

### Holes
- Q15: How does the app create accounts or set passwords, given the document only covers sign-in? Where do users rows come from? (author: The document does not say how users rows are created or how password_hash is set. The brief puts sign-up and password reset out of scope and says the users table already exists. I do not know the existing process. Added as an open question.)
