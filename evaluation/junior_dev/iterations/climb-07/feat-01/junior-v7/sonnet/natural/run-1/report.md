## Review of feat-01 (junior-v7, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Step 3: noted that 'active' includes the retry wait, so a click then returns the same export (Q1).
- Table: stated that every row write sets updated_at, so it is the heartbeat for queued and running rows (Q3).
- Step 3 stale rows: made it one conditional UPDATE in the click request, then repeat the insert, and return the winner if it conflicts again (Q8).
- Step 4: said which export the page shows after a click or a stale replacement (Q4).
- Step 5: said the loaded row holds the user, report and query_string.
- Step 6: added parsing query_string with the Row API parser, where a parse error is a failed attempt (Q6).
- Step 6: stated that dead-worker attempts still end in on_final_failure, and added a concurrent duplicate delivery bullet with no lock (Q2, Q7).
- Step 7 and open questions: recorded that repeated email failure leaves the user with no link, as a new open question (Q5).
- Step 8: stated that on_final_failure also runs after timeout or worker death (Q2).
- Merged the 'Background and decisions' section into a summary, a terms list, a shared-rules list and a data section; the summary is now 3 sentences and does not retell the steps.
- Merged the four 'Decisions' bullets into their owning places: record in the primary DB goes under the Primary term, unique index under the table, deterministic key under the object_key column, streaming under step 6.
- Added definitions for Read replica, Primary, Signed URL and Active export; folded the earlier 'dead worker counts as failed attempt' and 'on_final_failure runs once' facts into the Job queue term.
- Added a Rules-that-apply-throughout list (same permission/parser, replica only, out of scope) so these are said once, not at each step.
- Cut duplicated text: replaced 'Why buffer' and repeated replica/never-primary lines with a single rule; folded 'Memory' and 'Time' into one size check; removed the separate state-machine bullet list in favour of one line.
- Added from the junior's questions: a click during a retry wait returns the same export; every row write sets updated_at; poll shows the newest export even after a stale row is replaced; stale-row recovery is one conditional update then a repeat insert; worker parses query_string with the Row API parser; concurrent duplicate delivery needs no lock; dead worker on last attempt still triggers on_final_failure; email failing on all attempts leaves the user with no link.
- Added open question 3 (success email fails on all attempts).
- Left out as unneeded: the exact format of the failed-email wording and any lock or takeover mechanism.
- Kept every number, limit and setting from the first version (10,000 threshold, 500/5,000 page sizes, 45 s deadline, 8 MB/5 MB parts, 113 parts, 10,000-part limit, 3 h stale, 2 min lost enqueue, 5 s poll, 64 KB payload, 24 h/7 day rules, email template names, all tests).
- Separated how the system runs from release checks; the tests section now follows the runtime steps.

### Holes
- Q5: Step 7 sets `done` before the email is sent, and the page says 'Check your email'. If the email keeps failing through all attempts, the user never gets a link. What does the user see and can they ever get the file? (author: If the email fails on every attempt, the row stays `done`, the page says 'Check your email', and the user has no link and no way to get one. The brief gives no fallback and says nothing about minting links later. I did not invent one. I noted it in step 7 and added it to the open questions, tied to the existing fresh-link question.)
