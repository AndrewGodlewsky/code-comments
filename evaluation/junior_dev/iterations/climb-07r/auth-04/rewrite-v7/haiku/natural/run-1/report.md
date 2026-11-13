## Review of auth-04 (rewrite-v7, author haiku, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a summary of how password sign-in works today, since the plan changes an existing system; kept the 15-minute lockout, 14-day session, cookie settings and start_session behaviour in it.
- Added a terms list defining OIDC, the authorization code flow, PKCE, code exchange, ID token, sub, state, nonce, intent, return_to, Redis TTL and GETDEL, cookie, CSRF, bcrypt, lockout, start_session, google_identities and pending record.
- Kept the Mermaid flowchart in the same structure and branches, with the same node logic. Made every label self-contained, and changed the login success label to say return_to, since the start step stores it. Added the email_verified_at update to the confirmation success node, from the decisions list.
- Replaced the scattered state notes with one lifecycle table covering each permanent and temporary item, where it lives, its lifetime and what removes it. Removed the duplicate statements about state.
- Put all failure behaviour into one table with the step, what goes wrong, what the user sees and what changes. Steps keep only the actions and data, and point to the table.
- Wrote the numbered steps for the diagram's notes: what starts each step, what it does, which data it keeps, and the session rule shared with password login.
- Moved the database migration into a separate rollout section, apart from how the system runs.
- Kept every decision for the owner with its reason, and grouped them under a section before the open questions.
- Added one open question the brief did not raise: GETDEL runs before the cookie check, so a mismatched callback can burn a real user's state record. The plan is unchanged.
- Kept all brief requirements and facts: PKCE, state, nonce, scopes, 10-minute round trip and 10-minute confirmation, sub-only matching, one-link rules, the lockout behaviour, Cancel handling, unlink rule, and the reset-email message. Cut no requirement or limit. Removed the codes that pointed to other items, and avoided repeated facts.

### Holes
- None.
