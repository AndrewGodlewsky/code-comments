## Review of auth-01 (simplify-only, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Added an opening summary of how the existing app works today and how the login flow goes, before anything else.
- Added a short Terms section (session ID, id_hash, idle limit, absolute limit, lockout) in plain words.
- Moved the sequence diagram up, right after the terms and decisions, and put the detailed notes after it.
- Replaced the loose 'Rules not shown on the arrows' section with seven numbered steps, each with trigger, action, data and failure handling.
- Merged the separate Email handling and Login transaction rules into step 1, and the Order of checks into steps 2 and 3.
- Merged the Clearing the cookie note into the logout step, and folded the Scope notes into a short Not covered list.
- Cut the separate Session ID, How expiry is checked, and Removing abandoned sessions rows from the Decisions table. They are now covered by Terms and steps 5 and 6.
- Merged the four per-case Storage failures bullets into one table, with the per-step failure text kept inside each step.
- Removed requirement-number references from step text (kept only in the coverage table), and replaced the Open questions placeholder with an explicit None.

### Holes
- None.
