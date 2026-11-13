## Review of auth-04 (junior-v4, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Q1: removed return_to from the flow record and the terms. The start page now follows from intent, and next is marked as login only. Notes 3 and 11 updated to match.
- Q2: added cookie gstate, set at start and checked against the state parameter before GETDEL, with a new flowchart node, a state-table row and a failure row. Added note 2 explaining the login-CSRF risk it prevents.
- Q3: stated in the start step and note 1 that the link user_id comes from the current sid session, and that the callback compares that session's user with it.
- Q4: added definitions of sub and email_verified to the terms, and note 4 spelling out what the ID token checks mean.
- Q5: added note 6 on the lockout rule for Google sign-in and an open question on whether a linked Google sign-in should honour locked_until.
- Q6: added note 5 explaining why a matched account needs the password step.
- Q7: added Redis failure rows to the failure table (start, GETDEL, pending save, pending read and delete) and note 7 saying Redis holds no permanent state.
- Q8: clarified in the start_session node that the old sid row is the cookie the browser sent, and in note 3 that link does not call start_session.
- Layout: kept the diagram, put the summary and terms before it and the notes after it. Merged the separate email and ID-token rules into note 4, and folded the passwordless and unlink rules into the implementer notes. The CSRF token is now bound to the pending id in the confirm form. Added a CSRF failure outcome.
- Changed: The callback clears gstate on every response, and the CB node and state table say so (Q11).
- Changed: The PEND node says the callback sets gpl and redirects to /auth/google/confirm, so the browser reaches the confirm step (Q9).
- Changed: The pending record holds a CSRF token. The FORM node shows it as a hidden field, the POST checks it, and a term defines it (Q10).
- Changed: The email wording is fixed. Google's email is written once into users.email at creation and never kept elsewhere. The CREATE node names the source (Q14).
- Changed: Note 8 says a Google-only user signs in again with Google, and Forgot password sets a password (Q15).
- Changed: Note 13 explains what the sid check at callback stops (Q12).
- Changed: Note 14 says the confirm step uses only user U and replaces any other sid session on success (Q16).
- Changed: Added an open question about whether Redis rate limits cover the confirm form (Q13).
- Merged the 14 'Notes on the flow' into the numbered steps in section 4. Each note now sits in the step it explains (start, cookie check, ID token, password match, lockout, Redis, next, link check, confirm session).
- Merged the diagram-level outcome list and the separate 'What happens when things fail' table into one failure table in section 6, grouped by step. Removed duplicate rows and the separate 'Error or neutral' note, which is now one sentence in step 2.
- Cut the prose that repeated the state table. Kept one 'Where the state lives' table (section 7) and removed the duplicate lines about tokens and the Google email from it.
- Moved the Google-only account, unlink, password-reset and no-tokens rules into a short 'Other rules' section (section 5), kept apart from how the flow runs.
- Shortened the summary to a short description of today's login plus the new flow. Removed the repeated overview of the diagram, the duplicate terms, and the repeated explanation of the start step.
- Kept the Mermaid flowchart unchanged, so every entry point, callback outcome and the password-confirmation loop stay as before. Put the terms before it and the steps after it.
- Kept all five open questions, each shortened to one or two sentences. No behaviour changed, and no plan decision was altered.

### Holes
- None.
