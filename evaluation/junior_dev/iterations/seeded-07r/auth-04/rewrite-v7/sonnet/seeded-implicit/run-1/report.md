## Review of auth-04 (rewrite-v7, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Merged the old summary and notes into a short two-sentence overview plus a Terms section defining OIDC, sub, PKCE verifier, state, nonce, start_session, lockout and link
- Expanded the flowchart to cover both entry points, every callback outcome (Google error, bad state, exchange failure, unverified email, create, link, confirm loop, lockout, expiry)
- Added numbered steps saying what starts each step, what it does, where data lives and what happens on failure
- Added a Where state lives table with the user_identities schema, the Redis entries, their 10-minute expiry and what removes each
- Added a failure table including failed code exchange (error page, no retry)
- Decided: callback reads and deletes the state entry in one step for once-only use; pending link ID kept in a short-lived HttpOnly cookie; an already-locked account also discards the pending link; null password_hash fails the normal check with the generic message; UNIQUE-constraint races show the error page
- Kept all brief facts: scopes, no stored Google tokens, sub/email/email_verified only, 10-minute limits, refuse cases, settings linking without a password, unlink needs a password, same session as password login
- Added Build and rollout and Open questions sections (client ID/redirect URIs and the set-password prompt are unknown)
- Cut nothing of substance; the file is longer than 1.5x its first length because the first version omitted required state and failure coverage

### Holes
- None.
