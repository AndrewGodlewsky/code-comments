## Review of auth-04 (junior-v5, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Start node now generates a random bind value and sets g_bind to it, so Q2 is answerable from the diagram.
- Callback first node now clears g_bind in every outcome, including Cancel and state errors.
- Login-mode LG1 edge and OK node say which user_id goes to start_session.
- LG4 states the other column defaults, and the state notes say a Google-created user sets a password through Forgot password.
- Confirm GET page now redirects to the expired message when there is no live pending record, and the confirm form and POST carry a CSRF token.
- Link-mode insert explains why no password is asked.
- Reading guide says which failures are rendered pages versus redirects and that no sid session exists during login and confirm.
- g_bind and g_pending table rows explain what they are compared with or hashed to, and why g_bind exists.
- Callback node now says the server hashes the state Google echoes back to find the Redis key (Q9).
- Success node and reading guide say where next comes from and that the browser holds only sid afterwards (Q10).
- Race edge at LG5 says the losing transaction rolled back and left nothing (Q11).
- Confirm page CSRF token is an HMAC of the g_pending value, so it is stable across displays (Q12).
- Removed the separate re-check at confirm; the INSERT with unique constraints now does that job, and E_RACE says the cause is logged not shown (Q13).
- Reordered confirm: INSERT google_identities first, then DEL pending, so a database error does not lose the attempt; dropped the DEL-count check and the old CF13 node (Q14).
- Added where the client secret and JWKS come from, and that a slow or failed JWKS fetch is treated like a failed exchange (Q15).
- E_SESS now tells the user the session ended and to retry linking; failure table updated to match (Q16).
- Failure table gained rows for a unique violation at confirm and a database error at confirm; pending-record removal text and single-use notes updated.
- Reordered to: summary paragraph (with how sign-in works today), terms, diagram, step-by-step notes, state, failures, rollout, open questions.
- Replaced the 'Reading guide' bullets with a short summary and a Terms list (OIDC/PKCE, state, nonce, code_verifier, ID token, sub, JWKS, client secret, g_bind, g_pending, origin page, start_session, next), each in one line.
- Added a numbered step-by-step section (trigger, action, data, failure) covering start, callback, login mode, confirmation, link mode, unlink and success.
- Gave reasons where parts appear: why g_bind exists, why login start needs no CSRF, why a password is needed for an existing email, why no password in link mode.
- Answered the junior's step questions in the steps: what g_bind is compared with, that g_bind is cleared always, no sid during login/confirm, browser holds only sid after success, where next comes from, race-loop behaviour, confirm ordering (insert before DEL).
- Added a one-line note that Redis being down fails the start with a generic error, as a main-flow failure case.
- Merged duplicate statements: TTL/single-use bullets folded into the state table and steps; merged the ID token and JWKS failure rows into the exchange-failure row; removed the repeated 'nothing changed' wording in several rows.
- Trimmed diagram node text: dropped redundant explanations from OK, LG1, CF0, CF10 and others, now carried in the steps; structure and outcomes unchanged.
- Cut details the main flow does not need: the long single-use explanation, repeated cookie-clearing prose, and the Redis-table ownership prose that duplicated the table.
- Added a short Rollout section kept apart from runtime behaviour (migration, NULL-hash login change, then routes); this ordering is new and is a recommendation, not from the brief.
- Moved the JWKS cache lifetime into Open questions as undecided.

### Holes
- None.
