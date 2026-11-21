## Review of auth-04 (junior-v7, author sonnet, seeded-implicit)

Rounds: 2. Ended: teachback-correct.

### What changed
- Redrew the diagram to cover both entry points, callback validation, Google error, failed exchange, link mode, all login-mode outcomes and the confirm-password loop with lockout and expiry.
- Added a terms section (sub, state, nonce, PKCE verifier, ID token, mode, pending link, start_session).
- Added a state table giving where each piece of state lives (Redis keys, cookies, user_identities, sessions), its lifetime and what removes it.
- Added the oauth cookie binding the attempt to the browser, and stored mode, next and user id in the Redis attempt so the callback can tell link from login.
- Defined the pending link as a Redis entry with a 10 minute TTL, deleted on success, lockout and expiry.
- Numbered steps with failure behaviour, a failures table and a separate rollout section.
- Decided that password login with a null hash fails like a wrong password.
- Added an open question on whether unlink should re-ask for the password.
- Callback now clears the oauth cookie after deleting the entry, and the diagram edge says so (Q11).
- Added Redis failure handling at start, callback and saving the pending link, in steps and failures table (Q12).
- Spelled out the new-user creation (columns, no name, one transaction for both rows, rollback on failure) in step 7 and the diagram (Q13).
- Named the confirm endpoint POST /auth/google/confirm, takes only the password, user comes from the pending link (Q14); added to step 8 and diagram.
- Link mode with no session or a different user now shows an error page; split in the diagram and added to steps and failures table (Q15).
- Stated where next comes from and that start_session validates it as a relative path (Q10); the return page follows from the mode.
- Decided a known sub skips the lockout check and added the matching open question (Q9).
- Merged the summary and old per-step repetition: the opening is now one short paragraph covering how login works today and the shape of the change.
- Split the diagram's combined link-mode check into two nodes (session user matches; sub and user unlinked), and merged the two locked cases in the confirm loop into one 'account locked' edge, so the diagram matches step 8.
- Removed the step 2 repetition of the cookie lifetime and the cookie-clearing detail that duplicated the state table; the table now carries cookie purpose and clearing.
- Added one line to the state section on how the UNIQUE columns enforce one-to-one linking and why a changed Google email still works (only sub is looked up).
- Folded the answers about next, lockout on known sub, user row contents (no name column) and transaction rollback into the steps they belong to.
- Shortened step 9 and failure rows; merged 'other account linked' and 'user already has Google' into one failure row.
- Kept all brief facts: scopes, no stored tokens, fields read, 10 minute limit, once-only callbacks, neutral Google error, sub identity, email never changed, all unlinked-sub cases, lockout rules, settings link and unlink rules, same session.
- Left out the unneeded implementation details such as exact error page wording or retry behaviour; the Redis-failure handling stays as simply 'error page, nothing changes'.

### Holes
- None.
