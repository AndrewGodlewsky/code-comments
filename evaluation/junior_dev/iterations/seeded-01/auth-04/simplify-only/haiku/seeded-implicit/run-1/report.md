## Review of auth-04 (simplify-only, author haiku, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Worked from the draft and the brief only. No junior question transcript was included in this task, so no answer-driven edits were made.
- Reordered the document for a newcomer: summary of today's login first, then terms, then the diagram, then notes. Diagram and notes are kept separate.
- Cut the duplicated notes that repeated diagram branches. Each step now lists only what starts it, what it does, what keeps its data, and what goes wrong.
- Merged the Google error branch and the failed code exchange into one 'back to entry point with a neutral message' path, because both change nothing.
- Merged the 'errors show a message and change nothing' line into the failure table, one row per failure.
- Added what the brief requires and the draft lacked: state checked before the Google error branch, the 10-minute limit on the round trip, one-time use of state, the password-confirmation loop with the fifth-failure lockout, the 'already has a Google link' refusal, and the rule that Google never changes the stored email.
- Added a table of where each new piece of state lives, its lifetime, and what removes it.
- Clarified unlink. The draft said 'needs a password', which could be read as asking for it again. The brief only requires that a password is set. The re-prompt question is now an open question.
- Named the pending-link id as an HttpOnly cookie. This is a new detail I chose, not one the brief fixed.
- Recorded two decisions I made: refuse a second Google link on the same user in Settings, and show an error page with nothing created when a parallel request takes the same email.

### Holes
- None.
