## Review of cred-02 (junior, author haiku, natural)

Rounds: 5. Ended: teachback-correct.

### What changed
- Diagram: removed the Stuck --> [*] transition so Stuck has no outgoing path, as the brief's OPEN marking and the notes require.
- Added the POST /login response: a redirect to /login/second-factor with a two-field form, and the browser's next POST (answers Q1).
- Recovery codes: replaced the select-then-update with one atomic UPDATE filtered by user_id and code_hash, and stated sha256 as the hash with the reason (answers Q4).
- Confirm: specified one conditional UPDATE for the secret move and last_step, run in the same transaction as the code replacement and session deletion, with rollback on zero rows (answers Q6, Q7).
- Setup overwrite rule: starting setup again replaces the single pending secret (answers Q7).
- Disable: kept the totp_factors row with last_step and nulled the secret columns, and stated that other sessions are left signed in and listed as open (answers Q8).
- Expiry: stated that the 5-minute limit is noticed on the next request, not by a timer, since the diagram implies an automatic transition (answers Q5).
- Rate limit: suggested the per-IP limit for setup confirm and disable as well as the second-factor endpoint, and marked it as a suggestion since the brief sets none (answers Q8).
- Added a terms list for sealed, hash, challenge, pending secret, last_step, time step and recovery code, and defined the 6-digit, 30-second TOTP parameters (answers Q2).
- Added a failure table and an open-questions section covering restarts and lockout span, the 50-guesses-per-minute exposure, and other sessions on disable.
- Restructured into summary, terms, diagram, state, transitions, failures and open questions, and removed repetition between the diagram notes and the old step text. Every brief requirement and limit from the first version is kept.
- Added terms for start_session(), enqueue_email(), rate_limit() and conditional UPDATE, which the steps use and a newcomer may not know (Q13, Q9).
- Stated that 2FA is on when secret_sealed is not NULL, which the sign-in branch depends on.
- Added the single-use gate: delete the challenge with RETURNING before start_session(), and refuse if no row comes back (Q9).
- Added the order of checks on /login/second-factor: cookie, row lookup, expiry, field check, code check, then count (Q10).
- Stated that the fifth entry's code is checked before counting, so a correct fifth code succeeds (Q11).
- Rewrote Disable as one request that checks the password first, then the code, with a TOTP code subject to the last_step rule (Q12).
- Stated the three time steps tried and the tie rule for matching steps (Q13).
- Stated that the second-factor page gives one generic error and no count of tries left (Q14).
- Corrected the guessing figure in Open: the per-IP limit of 10 per minute on /login/second-factor caps one IP at about 10 guesses a minute, roughly 14,000 a day. The first version said about 50 a minute, which ignored that limit.
- Stated that Stuck is reached by a trigger that is not designed, and that the diagram arrow from Challenge to Stuck has no defined trigger yet.
- Moved the transition prose into numbered steps per flow, and kept the diagram as the only place the flow is drawn. Kept every fact from the brief and the first version, including the 10 recovery codes, the 5-minute challenge and the logout-of-other-sessions rule.
- Added a line that a rejected race (same code or challenge) is refused as a wrong entry, since the first version left that case unstated.
- Sign-in success is one transaction: the code's write (last_step or used_at) and the challenge delete commit together or roll back together. A refused challenge no longer burns a code for the real user (Q17).
- The recovery-code email is queued only after that commit, and the remaining count is read in the same transaction (Q18).
- The confirm step names pending_secret_sealed as the column it checks. The replacement step notes that a sign-in can make a new-secret code for the same step wait one step (Q15).
- The disable step names secret_sealed as the column it checks (Q15).
- The confirm step says the 10 codes are rendered once in its response. The failure table has a row for a lost confirm response (Q20).
- The diagram's challenge exit covers a missing, tampered or no-row cookie. The recovery-code arrow says the email is queued after commit (Q16, Q18).
- The confirm step states what a signed-out browser sees on its next request (Q19).
- Repeated wording was merged: the sign-in success step and the failure table no longer restate each other, and the setup confirm steps are one list. Every requirement in the brief is kept.
- Sign-in step 3: the lookup bullet now says the row gives user_id and that user_id is never taken from the form (Q24).
- Sign-in step 3: added a check that deletes the challenge row and cookie and goes to the password step when secret_sealed is NULL, because 2FA was turned off (Q22).
- Sign-in step 4: notes that secret_sealed is not NULL because step 3 checked it (Q22).
- Sign-in step 6: states that the remaining-codes count is discarded if the transaction rolls back, and the email is queued only after commit (Q21).
- Diagram: the Challenge to PasswordCheck label now includes 2FA turned off (Q22).
- Failure table: the session-write row now says the code and challenge are committed as spent, the cookie stays in the browser but matches no row, and the user sees an error page (Q23).
- Failure table: added a row for 2FA turned off while a challenge is open (Q22).
- Failure table: the pending-secret row now says what sign-in uses while a secret is pending (Q26).
- Open section: added expired challenge rows are not cleaned up, with a periodic delete left for the build (Q25).
- Changed: Q27. Added in 'Where new state lives' that each sign-in gets its own challenge row, and in sign-in step 6 that last_step is per user, so a step accepted in one browser is refused in the other.
- Changed: Q28. Sign-in step 6 now says the success path redirects to /home as start_session() does today, and that the remaining count appears only in the email, not on screen.
- Changed: Q29. Setup step 3 now says how the server identifies the user (the signed-in session's sid cookie, mapped to user_id) and which pending secret it checks. The failure table adds a row for zero rows changed on confirm: the form is shown again with the same message.
- Changed: moved the terms and the summary before the diagram and the state notes after it, as the skill layout asks. The lifecycle and sign-in notes now sit with the state they describe.
- Changed: merged repeated wording. The 5-entry rule, the 'start again' messages and the cookie-clearing behaviour each appear once in the steps, and the failure table lists the user-visible results. The fifth-entry redirect is now stated as going to /login, which is what the answer to Q16 decided.
- Changed: kept every fact from the first version, including the 14,000 guesses per day estimate, the suggested rate limits, the sha256-not-bcrypt reason for recovery codes, and the open items on Stuck, restarts, other sessions and expired rows.
- Kept every requirement, limit, number and rule from the brief and the first version: 2FA setup and disable, RFC 6238 settings (6 digits, 30-second steps, one step either side, reused steps refused), sealed secrets, hashed recovery codes, 10 codes per confirm, other sessions signed out on confirm, the 5-entry and 5-minute challenge limits, the email on recovery-code use, no wait for the email, disable needing password plus a code, and the Stuck state marked open.
- Kept all SQL statements, the challenge cookie attributes, the failure table rows (merged the two suggested-limit lines into one note), and the five open items. Added one open item stating the unchecked assumption about the session lookup code.
- Added a short sentence on how sign-in works today, before the terms, as the skill requires for a change to an existing system.
- Added terms that a newcomer would not know: 2FA, TOTP, time step, pending secret, last_step, seal/unseal and KMS, sha256, sealed cookie, sid cookie, challenge, start_session, enqueue_email, rate_limit, bcrypt_check, conditional UPDATE. Each is one line.
- Cut repetition. The same rules previously appeared three times (TOTP check in transitions, sign-in step 4, and disable). They now sit once in a Shared checks section, which the steps refer back to. The state-location and transition sections were merged into one Where state lives section, and the failure notes that repeated transition text were removed.
- Split each flow into numbered steps with a clear trigger, what the step does, and which data it keeps. Failure handling sits in the single failure table, plus the inline failure notes in sign-in step 3.
- Clarified the remaining-code count in sign-in step 5: it counts only codes still unused, read after the UPDATE in the same transaction. The earlier answer said it 'includes the code just used', which contradicts the email wording. This is a judgement call and should be checked.
- Added the entry rule (exactly one field filled) once in Shared checks, and referenced it from sign-in and disable.
- Left out detail the plan does not need yet: the recovery code format and length, and the exact email template wording. The brief does not set these.
- Kept the Mermaid diagram unchanged except that the notes beneath it now say that Stuck has no way out in this plan. The diagram itself was not altered.
- Left the disable transaction boundary unstated, because the first version does not specify it. Flagged for the reviewer as a possible question for a newcomer.

### Holes
- None.
