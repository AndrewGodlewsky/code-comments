## Review of sync-02 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Expanded the terse 8-item list into a self-contained plan with an overview explaining change_seq, tombstones, start_seq and why change_seq comparison makes replay safe.
- Gave every step the four required parts: trigger, data moved, where state is kept, and failure handling.
- Replaced POST /catalogue/full/start with GET /catalogue/position, since it only reads the current position, and spelled out the full, changes and 410 contracts, including how the server detects resync_required.
- Defined sync_state fields and made page save plus cursor update a single SQLite transaction so resume is exact.
- Added explicit steps for Wi-Fi pause/resume, interruption resume, catch-up, and atomic swap, which were implicit or missing before.
- Specified retry arithmetic (waits 2, 4, 8, 16 s across 5 attempts) and which errors are retried.
- Stated that old catalogue stays visible during a resync until the swap commits.
- Expanded the open question into what differs under each option without deciding it, and listed assumptions to confirm.
- Moved the retry and error-handling rules out of step 9 into a shared 'Rules that apply to every request' section, so step 9 is only incremental sync and other steps say 'per the retry rule' instead of pointing at step 9
- Expanded the terms list into a short glossary (change_seq, tombstone, keyset pagination, trigger, Wi-Fi only) and added a numbered five-point summary of how the download, catch-up and swap fit together
- Fixed a gap: catch-up needed a saved position but sync_state had none, so added catchup_seq (set in step 3, advanced in step 7, cleared in step 8) and used it in steps 5-8
- Removed the undefined 'resync requested' flag from step 3. Step 10 now calls step 3 directly, and a failed step 3 is self-healing because the stale position returns 410 again at the next trigger
- Step 4 now says the final page's transaction also sets phase = catching_up
- Step 5 now covers pausing catch-up as well as the page download, and notes the saved state is already correct
- Step 8 lists its transaction as numbered sub-steps, and step 9 clarifies that a failed attempt still counts against the 15 minutes
- Replaced after_id as a progress measure in the open question, since it is a product id and not a count, with the row count of products_staging
- Reworded several triggers and state notes to be shorter and more direct, and removed duplicated retry detail from steps 3, 4, 7 and 9
- Reworded the overview intro so the full download is described as including the catch-up phase.
- Added a 'Staging table' term and clarified the 'Wi-Fi only' term to cover every full-download request.
- Renamed 'How the pieces fit together' to 'The idea in five moves' with bold labels, so its numbered list no longer collides with the numbered steps.
- Added the reasoning for why catching up from start_seq misses nothing: later edits have a higher change_seq, and earlier edits were already visible to the pages.
- Rewrote the retry rule so it says plainly that there are 5 attempts with 4 waits (2, 4, 8, 16 s) between them.
- Step 1: said the page returns 'up to 500' products, since the last page is smaller.
- Step 2: described last_incremental_at as when incremental sync last started, matching step 9.
- Step 3: added the Wi-Fi condition to the trigger and listed it as an assumption.
- Step 7: noted that a tombstone deletes the row only if one exists.
- Step 8: restructured the transaction into a clean numbered list inside the State field.
- Tightened wording in steps 4, 5 and 6 without changing behaviour.

### Holes
- None.
