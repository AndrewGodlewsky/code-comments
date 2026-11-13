## Review of auth-04 (junior-v7, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Changed oidc_pending from SameSite=Strict to Lax: the confirm page is reached by a redirect chain that started at Google, so a Strict cookie would not be sent and the confirm step would always say expired.
- Added a Terms section defining start_session, sub, lockout, password reset email and next.
- Stated where next is validated and how it travels from start to the final redirect.
- Stated which users columns the new-user INSERT sets and that others use defaults.
- Explained how a Google-created user gets a password via the existing reset email.
- Stated that the confirm step takes user and sub only from the pending record and ignores any session.
- Added the reason the password is required even when the existing email is unverified.
- Defined one error page for Redis down, bad state and wrong session, with a link to /login.
- Moved oidc_state clearing to the callback entry for every outcome, removed it from the session node, and added a Cookies rule; a new start attempt also clears the old oidc_pending cookie.
- Added an Open questions section (locked accounts and email_verified_at on linking).
- Routes table: unlink row now says it needs a session and CSRF token, requires a password to be set, does not ask the user to type it, and ends on Settings with 'Google unlinked'.
- Rules: added an Unlink rule stating only password_hash is checked and no password is retyped.
- Flowchart: unlink start node shows signed in and CSRF checked; refusal now goes to Settings with nothing changed; added UOK node 'Settings: Google unlinked' after the delete.
- Failure table: unlink-with-no-password row says the Settings page refuses.
- Summary: now opens with how sign-in works today and states the main flow in a few sentences instead of three bullets.
- Terms: expanded from five entries. Added sub, PKCE flow, state/nonce/code_verifier and pending record, because the junior asked what names meant. Kept start_session, lockout, reset email and next. Folded the reason for not storing Google's email into the sub entry.
- Merged the Rules the diagram relies on section into short Notes on the steps, placed one per step after the diagram. Merged the separate Cancel-versus-failure, ID token, Email handling, Atomic writes, Locked accounts, Link mode, Unlink and Who-is-linked rules into those notes, and removed the cancel versus failure rule because the failure table and diagram already say it.
- Moved the one error page rule and the oidc_pending cookie rule into the failure section. Moved the cookie lifetime detail into the state table intro (every key and cookie lasts 600 seconds), removing repeated EX 600 and Max-Age wording.
- Cut the separate Cookies rule, since the state table's Removed-by column already says when each is cleared. Kept the one clause on refusals before the pending step.
- Kept the SQL, the flowchart (unchanged), the routes table, and every stated fact: scopes, 10-minute limit, 5 second timeout, lockout numbers, unlink rule, same session as password login, no tokens stored, and the open questions.
- Added Lax rationale for oidc_pending, the unlink CSRF/no-typed-password clarification, and that the new-user INSERT sets only email, email_verified_at and password_hash (moved into the state section).
- No rollout or build section exists in the source, so none was added.

### Holes
- None.
