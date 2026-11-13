## Review of auth-01 (junior, author sonnet, natural)

Rounds: 3. Ended: cap.

### What changed
- Added a 'Requirements this design must meet' section defining requirements 1 to 8 plus short system context, because the document cited numbers it never defined (Q1).
- Rewrote the login gate so one atomic GATE script refuses when 5 or more attempts already exist, otherwise records the attempt; this fixes the inconsistent 'more than 5' versus '5 or more' thresholds and states plainly that attempts 1 to 5 get 401 and the 6th gets 429 (Q2, Q3).
- Removed the separate FAIL script and its diagram step as redundant, and explained that a correct-password attempt is recorded and then erased by DEL lf (Q2, Q3).
- Added the post-lock behaviour (old entries age out) and the side effect that a success erases concurrent failures.
- Added a 'How the app talks to Redis' section: GATE, CREATE and CHECK are Lua scripts loaded at startup and run with EVALSHA (reload on NOSCRIPT); the other deletes are plain commands, and diagram labels now name the scripts (Q6).
- Reordered session fixation steps to DEL lf, then CREATE, then DEL old, and described the orphan new session if the 302 is lost (Q4).
- Stated that the abs_expires_at comparison runs inside CHECK on the Redis clock, and specified the deleted-user response (best-effort DEL, clear cookie, 302 /login), also in the diagram (Q5).
- Clarified which routes call CHECK (all except GET and POST /login and POST /logout) and what a signed-in user sees at /login, and updated the diagram note (Q8).
- Added a 'Closing the browser' paragraph explaining browser-session cookie behaviour and why it was chosen (Q7).
- Added to the failure table that Redis errors while clearing failures or deleting the old session also give 503, and that a Postgres failure still counts the attempt.
- Added a Reading the login form section: missing fields count as empty strings, go through the gate, and give the normal 401 (answers Q10).
- Rewrote the email normalisation note: over-254-character emails are cut for the gate key only, never used for lookup, skip Postgres and get the normal 401 (answers Q9).
- Extended the dummy-bcrypt rule to cover empty and over-long emails so timing stays uniform.
- Updated the diagram: step after receiving the form now shows missing field = empty, trim, lowercase and cut; the SELECT notes it is skipped for empty or over-long emails.
- Added the request-body size limit to the Left to the implementer list, since it bounds password length.
- GATE table row: GATE now takes a per-request random attempt nonce (16 random bytes as 32 hex characters) in addition to the email hash, so the document says where the sorted-set member comes from.
- State table lf row: stated member = nonce, score = Redis time in ms.
- Added a 'Why a nonce member' note under the key table explaining that same-millisecond attempts need distinct members to both count.
- GATE step 4: now says the attempt is added with member = the nonce and score = now in ms.
- Sequence diagram: the app step makes a random attempt nonce, and the GATE arrow passes it and records it as the lf member.

### Holes
- None.
