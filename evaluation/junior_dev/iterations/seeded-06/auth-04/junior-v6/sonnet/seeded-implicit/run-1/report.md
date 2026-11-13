## Review of auth-04 (junior-v6, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added the missing Redis key, TTL and contents for attempts (Q1) and defined attempt, state, nonce, PKCE verifier.
- Specified the callback outcomes for bad state, Google error, exchange failure and timeout, with where the user lands (Q2).
- Stated that known identity is matched on sub only, and the full unknown-sub decision order (Q3, Q4).
- Defined the pending link (Redis plus cookie, 10 min) and the wrong-password, lock and abandon behaviour (Q5).
- Defined start_session and what a session stores (Q6).
- Said the mode is saved server-side in the attempt, with a user check in link mode (Q7).
- Explained the Google-only unlink path via the existing reset email (Q8).
- Expanded the Mermaid diagram to cover both entry points, every callback outcome and the confirm-password loop.
- Added the state-lifetime table, the failure table and the migration.
- Added a real fix: POST /login must treat NULL password_hash as a wrong password.
- Added open questions for login CSRF binding and locked-account Google sign-in.
- Pending link now also stores `next` from the attempt; confirm-password success passes it to start_session (answers: where next comes from after the attempt is deleted).
- Confirm password step: a locked_until already in the future on open or submit rejects without a password check, deletes the pending link and returns to login with the locked message; table and diagram updated.
- Link mode step 4 now says how the signed-in user is found (sid cookie to unexpired sessions row, user_id must match the attempt) and that a signed-out, expired or different-user session gives the error page with nothing changed; diagram and failure table updated.
- Step 2: the settings start checks for a live session first (redirects to login if none) and answers with a 303 redirect to Google; added a failure-table row.
- Step 3: the callback keeps the attempt's contents for the rest of the request.
- Step 4: one sentence on why the sid cookie reaches the callback (top-level GET plus SameSite=Lax).
- Step 5: start_session receives the attempt's next from the same request.
- Step 6: spelled out which users columns a Google-created user gets and that no profile data is stored.
- Step 7: defined the existing password rules and where the stored user is loaded from.
- Step 8: said which email the reset goes to and what happens to sessions and the Google link afterwards.
- Terms: start_session now lists the sid cookie flags.
- Open questions: explained the login-forgery attack and why state and nonce do not stop it.
- Added a short account of how sign-in works today at the top, and said why the flow is shaped around one start endpoint and one callback.
- Added a 'lockout rules' term so the confirm-password step no longer points to 'the existing rules'.
- Merged the two 'Start' steps' repeated text, and moved the answers to the questions (next kept in pending link, locked-on-open case, SameSite=Lax cookie on return, 303 redirect, next passed through the callback, no profile data read, reset email goes to users.email) into the steps where they apply.
- Merged the confirm-password rules into three cases (already locked, wrong password, right password) instead of repeating the lock text twice.
- Reworded the build section into a separate 'Build and rollout' section and kept the diagram unchanged.
- Added rows to the failure table for Redis down, unique conflict, and the email's user having a different Google account; these were in the steps but missing from the table.
- Cut the repeated explanation of the lockout counting and the repeated mention that the mode comes from the attempt.
- Kept all fixed facts: 10 minute limits, 10 second exchange timeout, 14 day session, 15 minute lock after 5 failures, unlink rules, no tokens kept, NULL password_hash handling, both open questions.
- Left out the exact HTTP detail for how the pending cookie is named, and library choices, as nothing asked for them.

### Holes
- None.
