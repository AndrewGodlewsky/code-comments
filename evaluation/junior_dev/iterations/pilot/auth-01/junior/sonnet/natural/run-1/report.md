## Review of auth-01 (junior, author sonnet, natural)

Rounds: 1. Ended: teachbacks.

### What changed
- Added a 'Context and requirements' section stating the existing system and all eight requirements, because the junior could not see the brief (Q1, Q2).
- Explained the two-instance problem in the Context section and the first Postgres bullet (Q2).
- Specified that a missing cookie skips the database in protected requests and logout, and defined $1 as the hash of the cookie (Q3); updated the diagram with a 'no sid cookie' branch.
- Explained what the advisory lock locks and when it is released, and added SET LOCAL lock_timeout of 5s with 503 on timeout so a stalled request cannot block others forever (Q4); updated the diagram and failure table.
- Clarified that the lockout row commits before the 401 and that the fifth failure gives no lockout signal (Q5).
- Added login step 10 saying 401/429 never touch the cookie or session, and defined the 429 page message and Retry-After (Q6); updated diagram arrows.
- Said that page data is loaded after the session UPDATE and that failure there gives the 503 page; added a diagram step (Q7).
- Said the sweep is a per-process timer that runs at startup and every 10 minutes, and what happens on failure or restart (Q8).

### Holes
- None.
