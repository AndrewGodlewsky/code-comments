## Review of cred-02 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered to the skill layout: summary (with how sign-in works today), terms, diagram, state locations, numbered steps, open questions.
- Replaced the 'How to read this' section with a short summary at the top; kept a short paragraph just before the diagram saying how the two parts connect.
- Added a terms list defining TOTP, time step, recovery code, challenge, seal/unseal, enqueue_email, rate_limit and pending secret, for newcomers to this stack.
- Merged the repeated 'failure' bullets into each numbered step and numbered the steps in the order they happen (start, confirm, password, second factor, lost phone, disable).
- Added a one-line reason where a newcomer would ask why: unconfirmed secret is inert, replace needs no current code, sha256 is enough for high-entropy codes, replay rule is stricter than required.
- Diagram: changed the SetupPending to Off edge to 'cancel' only, and moved 'start setup again (overwrites pending secret)' onto the SetupPending self-loop, since overwriting keeps the state pending rather than leaving it.
- Clarified in step 4 that a recovery code is accepted only if it matches an unused code (replacing the vague 'must also be a valid unused code').
- Merged the 'Lost phone with a recovery code' and sessions notes into the steps and table without losing any requirement; dropped nothing from the first version (all numbers, cookies, SQL, limits and rules kept).

### Holes
- None.
