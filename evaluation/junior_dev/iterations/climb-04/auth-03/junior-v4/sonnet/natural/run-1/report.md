## Review of auth-03 (junior-v4, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Diagram A: enqueue marked not awaited; job shown as {email address, link}, answering Q1 and Q3.
- Diagram B: POST /reset now finds the row by token hash and uses row.id in the UPDATE (Q2).
- Diagram B: added fail-closed handling when the breached list is unreachable (Q4).
- Diagram B: noted hash(new) uses the same hash function as login (Q7).
- Notes: removed the claim that the job is deleted once sent or dropped; replaced with an open question (Q8).
- Notes: stated what happens to a device after its session row is deleted (Q5).
- Notes: stated what a user sees on clicking an older killed link (Q6).
- Notes: made the rate-limit timing note consistent with the diagram (enqueue not awaited).
- Added an Open questions section with four items.
- Form carries the token in a hidden field from GET to POST (shown in the diagram and Data note).
- Normalise step now says trim and lowercase; added an Email address note and an Open question about how users.email is stored.
- Rate-limit count made explicit: all rows in the last hour, any state.
- F4 now also covers enqueue failure: log and alert, still generic 200, no retry; F9 refers to it.
- Corrected the timing claim: only the unawaited enqueue helps and a small timing difference is accepted.
- F8 now says the form is re-shown with a generic error and the error is logged.
- Password-changed job shape and content defined (fixed text, address from users, no link).
- Reordered for a newcomer: summary and how the system works today, terms, data, two flow diagrams, failure table, notes, open questions.
- Added a short plain-words terms section (reset link, token hash, live link, killed link, generic reply) and defined 'live link' once, replacing the repeated validity condition.
- Numbered the steps inside each diagram and removed the CHECK 2 / F1-F9 codes; each failure now stands alone in one table.
- Merged F1-F9 into a single failure table; merged F4 and F9 (same handling) and F5 into one row for bad tokens on load or submit.
- Cut diagram clutter: removed side-branch connector lines in flow A, and the duplicated 'identical body' annotation.
- Merged duplicate notes: Data and Email address notes folded into Terms, steps and open questions; Single use, expiry and Rejected passwords merged into one Single use note; Reset is atomic kept short; Password changed email note folded into flow B step 6.
- Shortened the rate-limit and timing notes and dropped the repeated statement that all branches return the same reply.
- Left out how the queue keeps job payloads from the Data note, since it is already an open question.
- Kept intent unchanged: no new mechanisms added.

### Holes
- Q4: What is the 'breached list' and where does it live? Is it a table, a file or an external service, and what happens if it cannot be reached? (author: Where the breached list lives is not specified in the brief. Added to Open questions. If it cannot be reached, the design now shows a generic 'try again later' error with the link left usable (fail closed, simplest handling).)
- Q7: Which hash function stores the new password (hash(new)), and is it the same one that the login flow already uses to verify passwords? (author: The hash function is not named in the brief. The design says to use the same one login verifies with. Listed in Open questions.)
- Q8: What do the 'retry 3x with backoff' and 'drop' do to the queued job, which holds the raw token? The notes say the job should be deleted once sent or dropped. Who does that deletion? (author: Unknown. The existing worker retries then logs and drops; I do not know whether the queue keeps payloads afterwards. I removed my earlier claim that the job is deleted by someone, and listed the question as open.)
- Q10: The request flow says 'normalise email'. What does normalising do here, and does it match how the email is stored in users? (author: Normalising means trimming and lowercasing the address before lookup. I do not know whether users.email is stored that way. Added to Open questions; the lookup must match the stored form.)
