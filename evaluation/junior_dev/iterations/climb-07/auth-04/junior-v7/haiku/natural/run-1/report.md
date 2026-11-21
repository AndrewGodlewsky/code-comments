## Review of auth-04 (junior-v7, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Summary rewritten to say how password sign-in works today, then what the design adds, in three sentences.
- Terms section added (sid, start_session, lockout, OIDC, ID token, sub, authorization code, PKCE, state, nonce, txn, link record, GETDEL, TTL).
- Diagram: Cancel and did-not-finish now go back to the page the flow began on, not a single start page.
- Diagram: callback check now states cookie and state parameter both present and equal, plus Redis txn exists.
- Diagram: settings entry now states the sid check is a live sessions row.
- Diagram: Create branch adds a unique-violation path that rolls back and shows the login page message.
- Diagram: commit now checks in the DB transaction whether the sub is already linked to this user (earlier commit whose Redis delete failed), and the commit-failure path loops back to the prompt.
- Diagram: Redis delete after commit is shown as its own step, with a logged error that does not block sign-in.
- Notes on the flow: steps 1 to 9 added, each giving what starts it, what it does, which data it keeps and its failure handling, without repeating the diagram.
- Lockout decision recorded: Google sign-in for a linked sub is allowed while locked (moved from Things to confirm into the flow).
- Unlink section added (it was missing from the diagram): caller from sid, CSRF, success message, sessions untouched, zero-row message split by whether a password exists.
- Failure table: added rows for settings already-linked, create unique violation, commit failure, Redis delete failure after commit, unlink with no link, Redis outage at prompt; removed duplicate wording.
- Things to confirm: items 1 and 5 folded into the flow and failure table; items 2 to 4 kept as short open questions at the end, labelled as proposals.
- Where-state-lives tables and both SQL statements kept as written, with the Redis TTL authority sentence and the reason for Redis kept.
- Note 1 (Start): added how the start endpoint reads next, keeps it only when it is a relative path on the site, and falls back to /home.
- Note 7 (Password prompt): the callback redirects to GET /auth/google/confirm instead of rendering the prompt, and Cancel is a POST to /auth/google/cancel with the CSRF token.
- Note 9 (Finish): start_session first deletes the sessions row of any existing sid cookie, as password login does.
- Added note 10 (Password login on a Google-only account): NULL password_hash is treated as a wrong password, and such accounts never reach the prompt. This resolves the former open question 1, which was removed and the remaining questions renumbered.
- Failure table: added a row for a Redis failure when the callback writes the link record after GETDEL (error page, start again, nothing changed).
- Failure table: added a row for password login on a Google-only account (same generic message, failed_logins plus 1).
- Summary rewritten as three sentences: how sign-in works today, how Google joins that flow, and why both entry points share one start and callback.
- Added a Terms section defining every name a newcomer would not know: sid, sessions row, start_session, next, lockout, bcrypt, Reset email, Redis, TTL, GETDEL, OIDC, ID token, sub, authorization code, PKCE, state, nonce, txn, link record, entry, page the flow began on, form CSRF token, unique violation.
- Mermaid flowchart kept. Changed the Cancel and failed-exchange messages to go back to the page the flow began on, added the 303 redirect to the confirm page with Cancel as a POST, and added the Redis link-write failure edge (E_LINK). Also changed the lock edge to say a locked account still signs in with Google.
- Start step: defined the Settings sid check (live, unexpired sessions row), how next is kept or dropped, the SHA-256 hash reason, and the cookie and scope values.
- Callback step: defined what counts as a mismatch, and that a mismatch does not run GETDEL. Explained why the Google error is only checked after state passes.
- Login step: added the rollback row for a create unique violation, the decision that a locked linked account can sign in with Google, and the Redis link-write failure. Stated the lowercased email match.
- Password prompt step: merged the separate prompt, submit and cancel notes. Stated that the form does not name a user, that the 10-minute TTL runs from the callback and wrong passwords do not extend it, and that the loop never dead-ends.
- Commit step: added the already-linked-to-this-user branch, the commit-fails path that keeps the record, and the Redis-delete-fails path. Order is DB commit first, then Redis delete.
- Finish step: stated that the old sid session is replaced, not kept. Settings linking does not call start_session.
- Password login step: stated that NULL password_hash is treated as a wrong password, so the login page never reveals which accounts have a password. Moved this out of Open questions because it is now decided.
- Added an Unlink section: caller from sid, CSRF, the single DELETE statement, the two zero-row messages, success message, and that sessions are untouched. Kept the SQL statement in this section.
- Existing-file facts added: the reset email's one-hour validity and its deletion of all sessions, and the POST /login generic message. These were not in the first version and are taken from auth_flow.md and the answers.
- Merged repeated facts: the flow notes and failure text now appear once, with the failure table as the only place for failure outcomes. Removed the separate background and existing-files section.
- Moved the CREATE TABLE and ALTER statements into a Build and rollout section, apart from how the system runs. The unlink DELETE stays in its runtime section.
- Redis outage and the failed link write are now rows in the failure table, which the first version kept only in the Things to confirm list.
- Open questions: kept email_verified_at on a password-confirmed link and CSRF as the two open items. Removed the NULL password_hash question and the Redis outage item because both are decided in the body.
- Checked every requirement of the brief and every stated fact of the first version against the rewrite, and kept them all. The file is longer than the first version by roughly one third, mostly in the Terms section.

### Holes
- None.
