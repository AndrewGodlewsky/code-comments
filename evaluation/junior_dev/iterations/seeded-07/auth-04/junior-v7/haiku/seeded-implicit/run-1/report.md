## Review of auth-04 (junior-v7, author haiku, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Redrew the diagram so both entry points (login and Settings), every callback outcome and the password-confirmation loop each have their own branch.
- Fixed the diagram's arrow from 'Match or create account' straight to start_session. The case that creates a new user now goes through the create step, and the confirm case is separate (Q5).
- Added the attempt record (Redis, state, nonce, PKCE verifier, purpose, next path, 10-minute life, deleted when read) (Q1, Q2).
- Added the pending-link record and the oidc_pending cookie for the confirm page (Q6).
- Added the Settings link path, which uses sub only and checks the session (Q8).
- Added Google error handling (cancel, unknown state), with the neutral message and error page (Q9).
- Added a failure table covering the failed code exchange, expired or used state, and each refusal.
- Added a where-state-lives table with the removal rule for each piece of state.
- Added the unlink rule using password_hash, and the note that password-less login gives the generic message (Q10).
- Added a short description of today's login and start_session, and defined the terms a newcomer needs.
- Recorded two open questions the brief leaves unanswered (lockout on Google sign-in, email_verified_at on linking) and one assumption about CSRF on the confirm form.
- Summary cut to three short paragraphs. It now says how sign-in works today before describing the change, and it no longer repeats the steps.
- Terms: added definitions for OIDC, the authorization-code flow, Redis and the scopes, and kept the existing terms. Each is one plain line.
- Diagram: the session-ownership check for Settings linking is now drawn (it was only in the failure table). The confirm-loop nodes are renamed for clarity. The Recheck branch now goes to its own refusal node that deletes the pending link, which matches the failure table.
- Notes after the diagram cut to three points that the diagram cannot show (state lookup, confirm page entry, Google email never stored).
- Steps: each step now says what starts it, what it does, what data it keeps and what happens on failure. Ordered checks are numbered in the callback and the confirm page. Step 4 now says why a linked user with a changed Google email still reaches the same account.
- Merged the two link-conflict outcomes on the confirm page (error page versus refusal) into one: refuse with a message, link nothing, delete the pending link. This was an inconsistency between the first version's diagram and failure table.
- Added a failure row for a database write failure on Settings linking, and a note that the server checks unlinking rather than the page. These are the simplest handling the brief allows; they were not stated in the first version.
- Kept every requirement, limit, number and setting from the brief and the first version, including all failure rows, the schema changes, the state table, the unlink rule and all three open questions.

### Holes
- None.
