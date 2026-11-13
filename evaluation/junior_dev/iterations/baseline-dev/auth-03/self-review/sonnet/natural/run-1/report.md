## Review of auth-03 (self-review, author sonnet, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short PIECES section so a reader new to the stack sees how browser, API, Postgres, queue, worker and mail provider connect.
- Rewrote diagram A as a numbered sequence instead of a tangled multi-column layout with crossing branch lines; removed the 'all four branches converge' box (there were three outcomes, not four).
- Made A consistent with the timing note: the generic 200 is now shown being sent first, with the work done afterwards, replacing the vague 'enqueue after responding' advice.
- Simplified the diagrams' column layout to two or three lanes and aligned wording across A, B and C.
- Replaced jargon such as 'burn' and 'kills' with plainer wording (used up, replaced) while keeping the original meaning.
- Clarified the Referrer-Policy rationale, the conditional UPDATE in the GET/POST note, and that the 'password changed' email is queued after COMMIT.
- Moved the sessions-in-one-transaction rationale next to the other design notes and put the failure table last.
- Renamed the opening block to SYSTEM and added a short legend under the table stating that only sha256(token) is stored, what used_at NULL means, and that h = sha256(token).
- Reworded the table comment on used_at and rate-limit counting so the 'rows kept' reason reads directly.
- Used full sentences with 'Stop.' style consistency in flow A and added 'to the email queue' on both enqueue steps.
- Clarified that the token sits in a hidden form field in B.
- Made 'hash(password)' consistent and simplified step 2 wording in C.
- Made the worker line explicit that its retry behaviour is existing behaviour.
- Expanded the transaction note to say it also covers burning the link, since that is what the transaction actually protects.
- Added a note that the one-day cleanup does not affect the one-hour rate-limit window.
- Clarified that the row lock is per account in the race-safety note.
- Added a DEFINITIONS block that defines 'h', 'live link' and a single 'token check' (missing, used, replaced or expired), so B and C reference it instead of restating or saying 'exactly as in B'.
- Made C step 3 explicit: the users update and sessions delete use the user_id returned by the link UPDATE, and the 0-rows case says what it means.
- Clarified in A step 3 that the hourly count includes used and replaced rows.
- Changed 'in the background' to 'after replying' for plainness.
- Retitled the transaction note to say what it covers and tightened its wording.
- Removed the repeated definition of used_at semantics and minor wording redundancy; content, format and failure table are otherwise unchanged.

### Holes
- None.
