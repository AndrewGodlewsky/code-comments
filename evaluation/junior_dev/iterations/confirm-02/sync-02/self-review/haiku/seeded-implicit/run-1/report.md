## Review of sync-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a short list of terms (product, change_seq, tombstone, keyset pagination, staging, swap, Wi-Fi only) so a reader new to the project can follow the plan.
- Added a short section on how the full download and incremental sync fit together, including why change_seq decides which version wins.
- Each step now states what starts it, what data moves, where state is kept and what happens on failure, as the brief requires. The draft did not cover these.
- Step 1 now says what each endpoint takes and returns, including start_seq, next_after_id, has_more and the 410 reply.
- Step 2 now says what each table and each sync_state field holds, and notes the storage cost of two copies (about 1.6 GB).
- Step 3 now covers Wi-Fi pausing, resuming from the saved cursor, and the one-page-at-a-time rule.
- Step 4 now covers the catch-up from start_seq, the swap in one transaction, and why reps see no partial catalogue.
- Step 5 now spells out the apply rule (skip older changes, delete on tombstone, otherwise insert or replace).
- Steps 6 and 7 now give the exact wait times (2, 4, 8, 16 s) and say that the 5 attempts are per request.
- Step 8 is now a full step covering triggers and the 15-minute throttle, rather than a single line.
- Recorded three choices the brief does not cover, so the reader can see them: catch-up runs on Wi-Fi only, 4xx responses other than 410 are not retried, and the 15-minute throttle is measured from the start of the last run.
- The open question is kept undecided, with the two options stated and a note on what the plan does until the swap.
- Added plain-language definitions for SQLite, transaction, staging, the three saved positions (start, catch-up, last) and the HTTP status codes used (5xx, 410, other 4xx), so a reader outside the project can follow the steps.
- Step 3: stated that a request already in flight finishes and is saved when the device moves to cellular (the original wording, 'the page already in progress finishes', was ambiguous).
- Step 3: stated that a page is saved all at once or not at all, so an interrupted page is simply asked for again.
- Step 3: added that a paused download resumes when Wi-Fi returns during an open session. The brief requires this, but the original plan only resumed at launch or return-to-foreground triggers. This is a gap I fixed, not a new decision.
- Step 4: clarified that catchup_seq starts at start_seq. The original said 'since=catchup_seq, starting from start_seq', which was unclear.
- Step 4: explained the swap as delete-then-copy inside one transaction, so the mechanism is explicit.
- Step 5: stated the apply rule's case where no stored row exists (the change is inserted, or a tombstone does nothing) and that last_seq is saved with each page.
- Step 1 and step 6: removed the implied server-side wording so 'not applicable' is clearly about the server. Step 8: reworded the 15-minute rule so the counting of failed runs is explicit. Other wording tightened; all steps, numbers, the open question and the structure are unchanged.
- Added a plain-language definition of a page, and expanded the definitions of tombstone, transaction, staging and swap so a reader new to the project can follow the plan.
- Explained the change_seq rule in one place (higher number is newer; skip older or repeated changes), and linked it to step 5.
- Added a phase field to sync_state (downloading or catching_up). Previously step 8 said to resume step 3 even when the download had already finished and was in catch-up, which was ambiguous.
- Step 8 now says when last_incremental_at is saved (at the start of each run), so the 15-minute rule can be implemented.
- Step 1 is now marked as server-side only, and the empty-cursor and last-page rules are stated plainly.
- Step 3 starts list and step 4 wording were tidied; 'Then run step 4' now reads 'Then go to step 4', and the page loop is written as explicit numbered sub-steps.
- Step 4 now states that catch-up is part of the full download and so runs on Wi-Fi only, as a plain sentence instead of a note about the brief.
- Step 6 now sets phase to downloading on resync.
- Kept all decisions, the step structure, the Starts/Data/State/Failure format and the open question unchanged.

### Holes
- None.
