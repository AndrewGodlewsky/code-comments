## Review of auth-04 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a plain-language glossary (sub, state, nonce, PKCE, attempt) and a table of new pieces with route names so a reader new to the stack can orient.
- Rewrote the flowchart to cover everything the brief requires: both entry points, every callback outcome, the failed code exchange, the settings link path, the full password-confirmation loop with lockout and discard, and unlink.
- Added a state section for permanent (Postgres) and temporary (Redis and cookies) items, with contents, lifetime and what removes each.
- Added a failure table covering every failure mode, what the user sees and what changes, including the failed code exchange.
- Specified how the one-time use of a callback works (the attempt is deleted on first read) and how the 10-minute limits apply.
- Added the exact exception and ordering rules: email matching only at sign-in, a settings link without a password, a conflict check before asking for a password, and how users with a NULL password behave at /login.
- Defined the message texts and the two failure styles (error page versus return with a message).
- Flagged one assumption (lockout does not block Google sign-in of an already linked user) instead of leaving it implicit.
- Removed vague notes such as 'Errors show a message and change nothing' and 'Uses the normal session', replacing them with concrete behaviour.
- Added a definition of 'pending link' to the terms list
- Added a one-line reading guide before the flowchart and labelled the 'Back to start' node so it matches the notes
- Rewrote the failure-modes section so each cause is listed plainly, and said precisely that the only change is the already-deleted attempt
- Rebuilt the messages table: split the muddled 'Confirm expired, account locked, or link conflict' row, and moved the page into its own column instead of ambiguous '(start page)' notes
- Reworded the lockout-on-Google-sign-in assumption so it is clearly labelled and says what decision is needed
- Explained why the dummy-hash comparison matters (timing) rather than saying it 'costs nothing extra'
- Added a short note that GET on the confirm page follows the same expiry rule as the submit step shown in the diagram
- Minor wording cleanups: 'normal user deletion', 'a code works only once', 'deletes their sessions' consistent with the existing reset behaviour
- Added a short Context paragraph explaining the stack pieces (Redis, start_session, existing lockout) for readers new to the project
- Defined 'attempt' with its 10-minute limit and tightened the 'pending link' definition
- Removed minor wording redundancies and smoothed a few sentences; flow chart, tables and behaviour left unchanged

### Holes
- None.
