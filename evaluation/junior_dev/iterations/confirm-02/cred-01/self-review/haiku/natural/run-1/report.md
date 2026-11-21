## Review of cred-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a plain-language opening paragraph that explains the server-generated token, the one-way SHA-256 hash, why there is no validity cache, the 15-minute write throttle, and the per-user row lock, with terms like transaction defined.
- Added a short 'Reading the diagram' section that defines the arrow types (request, response, lost response, background write) and the alt and opt blocks.
- Added a note to flow 3 that says what happens when the last_used_at write fails.
- Added a note to flow 4 that says what happens when the revoke response is lost and why repeating the call is safe.
- Reworded the row-lock note to say what the lock does in plain terms (a second create for the same user waits).
- Explained the 401 generic body as not revealing which check failed, and the 'Validity' row as the next request after a revoke being rejected.
- Explained that token_hash is indexed so each request's lookup is quick, and that the write throttle reads last_used_at from Postgres so it survives a restart.
- Rewrote the token-format item to define base62 and rejection sampling, and the hashing item to show the 190-bit calculation and why salt and slow hashing are not needed.
- Kept the diagram's structure, participants, failure branches and the table and section layout unchanged; no change to design intent or open items.
- Added a short "What this design does" opening that explains bearer tokens, the purpose of the hash, and why revokes take effect immediately, so a reader without project context can follow the rest.
- Added a "Terms used" list for bearer token, hash, CSPRNG, idempotent and session cookie.
- Split the long "How the design works" paragraph into shorter paragraphs, one idea each, and explained the transaction and row lock in plain words.
- In the create flow, noted that the server cannot tell whether the create response arrived, and that the browser must not retry on its own. This was previously only in the failure table.
- In the create failure table, added that a revoked or expired token does not block its name, to match the active-only uniqueness check.
- In the revoke diagram note, explained that COALESCE keeps the first revoke time on repeat calls.
- Rewrote the hashing decision so it states the arithmetic (62 to the power of 32, about 2 to the power of 190) and why a plain SHA-256 hash is enough, instead of the vague "no one can guess" wording.
- Clarified the write throttle: it still works after a server restart because it reads the stored value, not an in-memory timer.
- Diagram and table content otherwise unchanged in meaning: the same four flows, the same alt and opt branches, the same status codes and the same state locations.
- Added plain-language definitions for Postgres, transaction, row lock, endpoint, status codes and the generic 401 body.
- Explained in plain words what the per-user row lock and the last-used write throttle do and why they exist.
- Explained COALESCE and why a repeated Revoke is safe, using plain wording.
- Rewrote the revoke path as /settings/tokens/ID/revoke so the colon in the path cannot be confused with Mermaid syntax.
- Noted in the lost-create-response branch that the row shows in the list, so the user can revoke it.
- Explained the token character set and the rejection-sampling step with the concrete byte range 248 to 255 and the reason 256 does not divide by 62.
- Clarified that the token-management endpoints accept only the session cookie, and why that limits a leaked token.
- Shortened long sentences and split dense paragraphs. The four flows, the diagram structure, the state and failure tables, and all decisions are kept unchanged.

### Holes
- None.
