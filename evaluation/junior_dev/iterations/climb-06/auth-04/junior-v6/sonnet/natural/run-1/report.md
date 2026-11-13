## Review of auth-04 (junior-v6, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Endpoints table and flowchart: confirm now requires the app's CSRF token plus g_pending cookie; bad token goes to the error page (answers Q1).
- Flowchart: the password form names the matched account's email; the pending record is stated to hold only sub, user_id and next (Q2).
- check_password_with_lockout is stated to treat a NULL hash as a wrong password; added a line that a NULL-hash unlinked user cannot exist (Q3).
- Added decision 7: starting Google sign-in while signed in replaces the session named by the sid cookie (Q4).
- Failure table: new row for Redis failing after the attempt was consumed; Redis row narrowed to start and callback (Q5).
- Code-exchange node and open questions: Google endpoints and keys come from the cached discovery document, 5s timeout on each call (Q6).
- start_session description: deletes the row named by the sid cookie sent, and does not touch failed_logins or locked_until (Q7).
- Added decision 8 explaining CSRF protection on confirm.
- Confirm endpoint now uses an HMAC-of-pending-ID confirm token instead of the app's session CSRF token, because no session exists at that point (endpoint table, flowchart password form and check, failure table, decision 8).
- Noted that stored emails are always lowercased, so the email match is exact (state section and match step in the flowchart).
- Added an open question that the app's session-bound CSRF mechanism for Settings endpoints is not described in the existing files.
- Flowchart attempt node and callback check: the bind value is random, stored in the record, and compared to the g_bind cookie value (Q10).
- Cookies section: explained what g_bind is compared to and what it protects against; said the pending ID is 32 random bytes and the confirm token is computed when the form is rendered (Q10, Q13).
- Flowchart pending node: pending ID is random and the confirm token is computed at render time (Q13).
- Flowchart ending node and permanent state: start_session makes no other database change (Q11).
- Permanent state: added how a Google-created user can sign in later and what happens with a second Google account of the same email (Q12).
- Added decision 9: lockout is shared with /login, the only limits at confirmation are lockout and the 10-minute window, and why the locked check exists there (Q14, Q15).
- Failure section: one line on what the error page and back-to-origin messages show; open questions now cover the flash mechanism and rate limits on confirm (Q14, Q16).
- Reordered into the skill layout: one summary paragraph (how sign-in works today, then the Google flow and why it is shaped this way), a Terms section, endpoints, the flowchart, numbered step-by-step notes, state, failure table, decisions, open questions.
- Added a Terms section defining sub, state, nonce, PKCE verifier, attempt, bind value, pending link, confirm token, start_session, lockout, check_password_with_lockout, POST /forgot and next; moved the existing-system description into the summary and terms and cut the separate 'What already exists' section.
- Added a numbered 'Reading the flow, step by step' section after the diagram (what starts each step, what it does, where state is kept, what happens on failure), replacing the scattered notes.
- Merged the NULL-hash handling: the dummy bcrypt compare is stated once in the terms and once in permanent state; removed the repeat in the endpoint and failure text.
- Kept the diagram unchanged; kept every stated requirement (10-minute limits, 5 s timeout, lockout numbers, scopes, uniqueness rules, unlink rule, same session) and the Redis and cookie tables, failure table and all nine decisions.
- Dropped the long reasoning about the NULL-hash edge case to a single bullet, and trimmed the open-question wording; removed the 'Q' style references so each step stands alone.
- Left out details nothing needs yet: HMAC algorithm choice, flash-message implementation, exact error page design (kept as open questions).

### Holes
- Q16: What does the user see on the 'Error page' and the 'Back to origin page' messages, and how does a message get shown on the login or Settings page after a redirect? (author: The error page shows the short message from the failure table with no technical detail, and the back-to-origin messages are shown once after the redirect. How the app implements a one-time message after a redirect (flash mechanism) and what its error page looks like are not in the existing files, so I do not know. Recorded as an open question; I suggested reusing the app's existing mechanism.)
