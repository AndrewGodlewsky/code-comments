## Review of auth-03 (rewrite-v5, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added a opening paragraph describing how the existing mail system works today and the flow in two parts, with the reason for the worker minting the token.
- Added a Terms section (reset row, token, token hash, burned, generic message) and moved the data table description before the diagrams.
- Merged the long Notes into short per-flow notes placed right after the diagram, each with its reason in one clause (lock, count includes burned rows, kill old links at request time, worker mints token, uniform response).
- Merged 'burn the link' and 'logout everywhere' notes into the link-click notes; dropped the repeated explanation that used_at covers both cases into the Terms line.
- Cut diagram clutter: removed repeated connector rows, the empty arrows and duplicated generic-message text; kept the diagram form.
- Cut the 'Two submits race' row from the failure table and folded it into the link-click note; merged 'Token missing/wrong/expired/used' rows into one.
- Changed the failure table wording: 'Old link unchanged' now says 'earlier link unchanged' and the mail-fail row now says a metric is emitted, matching the silent-drops mitigation.
- Moved the silent-drops gap to a final Open questions section and removed the claim that a failed send counts toward the limit as a separate bullet (kept in the failure table).
- Removed the purge detail from a standalone note and kept it as one clause under the rate limit note.

### Holes
- None.
