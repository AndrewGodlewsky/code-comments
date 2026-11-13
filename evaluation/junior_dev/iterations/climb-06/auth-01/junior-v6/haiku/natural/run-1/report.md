## Review of auth-01 (junior-v6, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Added the exact INSERT for a successful login, with both deadlines computed by Postgres now(), in the Schema section, and put the same values in the diagram label for the INSERT (Q1).
- Added a 'One row' rule to Flow 2: the UPDATE's user_id is all the page needs, no second query, and the foreign key means a live session cannot point to a missing user (Q2).
- Added the dummy-hash rule: a constant bcrypt hash created once, shared by both instances, with the same cost as stored hashes; the cost value is listed as an open question (Q3).
- Defined 'clearing the cookie' with the exact attributes and Max-Age=0, and why the __Host- rules are satisfied (Q4).
- Added a 'Waiting for the lock' rule: the wait counts against the 2-second statement timeout, past which the user gets 503, and the wait includes the holder's bcrypt time (Q5).
- Put the sweep timer inside each app process, with the skip-if-still-running rule and restart behaviour in the Cleanup section (Q6).
- Stated that a successful login deletes whatever session the incoming cookie names, whichever user owns it, and that a garbage cookie deletes nothing (Q7).
- Added a Normalization rule covering trim plus lowercase, where it happens, and what it does not cover, and noted the trim as my addition (Q8).
- Added an Open questions section at the end: bcrypt cost factor not in brief, no user-deletion flow under the foreign key, hashtext lock collisions, and plus-addressed emails counted separately.
- Added a requirement-coverage pointer to the new Normalization rule and clarified the Cookie row in the Decisions table to point at the clearing rule.
- Added a summary that says how the system works today (server-rendered, two instances, no sticky sessions, shared Postgres with the unchanged users table) before the new design.
- Added a Terms section that defines every term a newcomer needs in one plain line, including cookie flags, __Host- prefix, advisory lock, bcrypt, dummy hash, sweep, statement timeout, fail closed, Retry-After, UPSERT and foreign key.
- Moved the schema into How data is stored and kept the Decisions table, Why Postgres, and both SQL statements as written.
- Answer 1: the success INSERT now states that Postgres sets both deadlines from now(), the transaction start time, so an advisory-lock wait does not move them.
- Answer 2: the one-row touch check now says the page is built from the returned user_id with no second query, reads the users row only if a page needs user fields, and relies on the foreign key so a live session never points to a missing user.
- Answer 3: the dummy hash is now a separate rule: a constant bcrypt hash of a random password, stored in app config, identical on both instances, same cost as stored hashes. The cost value stays an open question.
- Answer 4: clearing the cookie is defined concretely as a Set-Cookie header with the same attributes and Max-Age=0, with the __Host- reasoning.
- Answer 5: the lock-wait behavior is its own rule (counts against the 2-second timeout, includes the first attempt's bcrypt time, gives 503). Added an open question to confirm that Postgres applies the timeout to lock waits in this project's configuration.
- Answer 6: the sweep is described as a timer inside each app process, skipped when a run is still going, restarted on instance restart, with missed sweeps harmless. The three DELETE statements are now shown exactly.
- Answer 7: the old-cookie deletion on login is stated as intended, whatever the owner, with garbage and unknown cookies matching nothing.
- Answer 8: normalization is step 1 of login, covers trim and lowercase only, and gives the plus-address and dot examples.
- Added a failure-table row: a commit failure on the wrong-password path returns 503, not 401, because nothing was recorded. The first version did not cover this case.
- Added a cleanup note: the idle deadline never passes the 12-hour cap, so the sweep also removes sessions past their absolute expiry. This follows from the existing rule and is not a new behavior.
- Split the document into how the system runs (summary, terms, data, flows, rules, failures, coverage, trade-offs) and how to build and roll it out (a short Building and rolling out section for migrations, dummy hash creation, statement timeout and sweep timer).
- Turned the flows into numbered steps with the data each step keeps and what happens when it fails. The Mermaid sequence diagram is kept in full, with the success INSERT label reworded so it has no semicolons.
- Merged repetition: the 429 text, lock-wait rule, and the cookie-clearing description each appear once. The requirement coverage table now points to section names, not codes such as Flow 1 step 2.
- Kept every requirement, limit, number and setting from the first version: all eight fixed requirements, 5 failures, 10 minutes, 15 minutes, 429 with Retry-After, 30 minutes, 12 hours, 32 bytes, 43 characters, 1000-row batches, 10-minute sweep, 2-second timeout, all trade-offs and all open questions. Added four open-question and rule clarifications from the answers, so the file is longer than the first version but within about 1.5 times its length.

### Holes
- None.
