## Review of auth-04 (junior-v3, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Cookie goidc_state now holds the state value, and the callback compares it with the query state and the Redis flow record (Q1).
- Spelled out the settings callback check: sid must map to a live sessions row whose user_id equals the flow user_id (Q3).
- Added a terms section and notes on origin page, next, Cancel at Google, and the confirm Cancel button and walk-away case (Q4, Q6, Q8).
- Confirm POST now reads the token from the glink cookie and takes user_id from the pending record. The form carries no user id (Q5).
- The users insert and google_identities insert are described as one transaction (Q7).
- Made Redis key naming consistent as goidc:<state> and glink:<token>, and gave the glink cookie the token (Q1, Q5).
- Added the signed-out settings path (SIGNEDQ, redirect to login) to the flowchart, because decision 7 was not in the chart.
- Added a failure row for the user walking away at confirm, and a note that a linked sub skips password and email checks (Q2, Q8).
- Added an Open questions line about whether existing users.email values are all lowercase (Q7).
- Cut the repeated prose: the per-node notes now sit in one numbered Steps list after the diagram, instead of a separate Notes list that restated the same diagram nodes.
- Merged the 'Where new state lives' and 'Redis holds only short-lived data' lines into one state table with a single closing sentence.
- Merged the 'Decisions to confirm' list and 'Open questions' into one Open questions section, keeping each decision's default on one line. Decisions 4 and 6 were kept as written.
- Removed the separate Forgot password paragraph from the failures and kept one sentence under the failures table, since only the unlink row depends on it.
- Fixed a real gap in the diagram: the fifth wrong password (PLOCKSET) had no outgoing path. It now ends at the login page with the incorrect password message.
- Fixed a contradiction: the failures table said the next attempt gets Account temporarily locked, but the pending link was deleted, so the next attempt would have been 'sign-in expired'. The row now says the next Google attempt meets the lock at the confirm step, which holds because a new pending link is created and then checked for the lock.
- Fixed a routing mismatch: a settings callback with no live matching session went to the state-error box, which said 'existing session kept' and conflicted with the failures table. It now has its own node, SESSBAD, that says the flow is consumed.
- Added the 'Redis down at callback' path to the diagram. It was only in the failures table before.
- Shortened the diagram labels and removed nothing the brief requires: both entry points, every callback outcome, the password-confirmation loop, the failed code exchange, and the lock/cancel/expiry paths are still there.

### Holes
- None.
