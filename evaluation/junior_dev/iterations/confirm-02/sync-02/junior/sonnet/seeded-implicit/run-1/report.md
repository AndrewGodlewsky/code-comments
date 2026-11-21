## Review of sync-02 (junior, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added the server API section: start returns start_seq, full takes after_id and returns done, changes returns next_seq and has_more and 410 when too old; the first version never said what the endpoints take or return.
- Defined sync_state fields, cursor (a product id saved in the same transaction as its page), start_seq, last_seq, change_seq and tombstone in a Terms section.
- Specified catch-up: which call it makes, that it applies to staging, and the skip-if-not-newer rule, which was a bare 'compare change_seq'.
- Specified swap as one atomic SQLite transaction and its recovery after a crash.
- Said what 410 does to products and staging, and noted a download longer than 7 days cannot finish, because catch-up would get 410 each time.
- Said which failures are retried (network, 5xx) and which are not (other 4xx), with the wait sequence and what happens after the 5th attempt.
- Said incremental sync does not run while a full download is in progress.
- Noted that products stays empty until the swap, so the browse-during-first-download question stays open and undecided.
- Restructured into summary, terms, API, storage, numbered steps, failure table, build section and open questions.
- Server API: /catalogue/full now returns each product with its change_seq, and client rows store it, so the skip rule in step 4 can work (Q9).
- Step 1: routes by phase so a resume after a kill goes to step 3 or 4 instead of resetting at step 2 (Q12).
- Step 4: added that lower-id new products arrive via catch-up and that deleting a missing staged row is a no-op (Q10, Q11).
- Step 6: added that reps can browse mid-sync with pages visible per commit, and how a kill mid-sync resumes (Q14, Q15).
- Step 7: stated that 410 applies in step 4 as well, and what step 2 resets (Q13).
- Failure table: added a row for app killed during step 6.
- Client storage: added the roughly 1.6 GB free space need during a full download (Q16).
- Open questions: added that swap duration and read blocking are unmeasured (Q16).
- Changes endpoint: stated what an update change and a delete change contain (Q17).
- Changes endpoint: with no changes, next_seq = n and has_more = false, so the saved position stays put (Q18).
- Step 4: catchup_seq is set to next_seq per page, and when has_more is false it moves on to step 5 (Q19).
- Step 5: swap now clears last_incremental_at, and a sentence explains that edits after the last catch-up page arrive through step 6 at the next trigger (Q19).
- Step 1: Wi-Fi returning is a trigger only while phase = downloading; when idle it starts nothing (Q20).
- Rewrote the opening as a short summary of the main flow, naming the Postgres/no-API starting point and why staging is used.
- Added terms: catchup_seq and Transaction (junior kept asking what they meant); tightened the other term definitions.
- Merged the old 'compare change_seq when applying' and delete handling into one 'Applying a change' and 'Skip rule' pair in step 4, and made step 6 refer to them instead of repeating them.
- Moved the new-product-with-lower-id case and the delete-before-fetch case into step 4 where they apply; removed the duplicated explanations elsewhere.
- Step 1 now routes explicitly by phase, and Wi-Fi returning is limited to the paused download; step 2 states it is the only reset.
- Folded the endpoint payload details (full row on update, id plus deleted flag on delete, next_seq with no changes, 410) into the API section so steps need not repeat them.
- Kept every fact from the first version: 500 and 1,000 page sizes, keyset order by product id, 15-minute throttle, Wi-Fi only, 5 attempts with 2 s doubling, 7-day window, one-at-a-time pages, resume from last saved page.
- Added to retries that catchup_seq is also kept, and that other 4xx are not retried (decision recorded in the report).
- Left out as not needed: exact SQLite journal mode choices and library details; swap timing remains an open question.
- Open questions now hold only the undecided product question and the unmeasured swap time; Build and rollout stays separate from How it runs.

### Holes
- Q7: What is shown to a rep while the first download runs, and what if Wi-Fi drops or is not available when the download is needed? (author: Whether reps can browse during the first download is an undecided product question and is listed under open questions. As written, products stays empty until the swap. If Wi-Fi drops or is unavailable, the full download pauses (after finishing its current page) and resumes when Wi-Fi returns; existing data stays visible during a re-download.)
- Q16: The swap drops and renames an 800 MB table. How long does it take and does it block reads from products while it runs? Also, does the client need free disk for two full copies during the download? (author: I do not know how long the swap takes, or whether it blocks reads of products while it runs. That depends on the SQLite journal mode and has not been measured. Added to Open questions. On disk: yes, during a full download the device holds the live table and staging, about 800 MB each, so it needs roughly 1.6 GB free. Added to Client storage.)
