## Review of feat-01 (junior-v5, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Step 8 claim now applies only from queued, or from running with a lower stored attempt number, so duplicate delivery of the same attempt cannot start a second run (Q7).
- Each attempt writes to its own object key, and only the attempt whose CAS applies links its key. This replaces the earlier overwrite-the-same-key approach, which an earlier attempt could still hit (Q6).
- The step 10 CAS and the step 9 progress updates are guarded by the attempt number (Q5, Q6).
- Step 15 states which timestamp applies: attempt_started_at for running rows, created_at for queued rows. It also says what a user sees if a stale row's worker is still alive (Q8).
- Added step 7 so a user whose click was ignored sees a notice with the running export's filters. The plan also says there is no cancel (Q3).
- Replaced the '6a and 6b' reference with a plain description of the window between start_multipart and saving upload_id (Q4).
- Step 10 now names complete_multipart explicitly and says what the user sees if the process dies between complete_multipart and the CAS (Q5).
- Added one-line definitions for page view, report.view, row_id, reports.row_count, job queue, attempt, exports bucket, signed URL and at-least-once delivery. Each step now stands alone, and cross-references to open-question numbers were removed (Q1, Q2 and general clarity).
- Moved the throughput gate, formula-injection decision and verification into a separate Build and rollout section, so the runtime flow stands apart from rollout.
- Added a failure table covering every step.
- Added open questions on how jobs are dispatched and how long they can wait, and on whether a killed attempt is confirmed stopped (Q2, Q6).
- Rewrote the whole plan for a newcomer. It now opens with what the feature is and what the page does today, then defines the terms, then gives the steps in order grouped by part: the click, the background job, the page and download, and failures.
- Step 4: the stale-state check now runs before the insert on each click, and the insert is retried once if the blocking export is stale (Q9).
- Terms: added how the queue numbers attempts, retries failed attempts automatically, and sets the 60 s and 300 s waits (Q10).
- Step 10: the running banner shows rows written so far, with no total or percentage, because row_count is unfiltered (Q13). It also says the banner shows the last attempt started during the wait between attempts (Q11).
- Step 7: the job reads filters and cols from the export record, and a replica failure fails the attempt so the next one starts from row 1 (Q12).
- Step 8: states that unlinked objects from superseded attempts stay until the 7-day bucket rule removes them. No cleanup job (Q14).
- Step 13: states that the final-failure handler also runs after a timeout or dead worker, and that the error value's form is not known, with the fixed phrases used until then (Q15).
- Removed internal cross-references and codes (such as Q-numbers and bare step references in prose) so each step reads on its own. Merged repeated rules on the stale check and the upload-ID window into single statements. Kept the failure table, build section and open questions, and moved the build section into its own section apart from how the system runs.
- Kept the intent and every fixed rule from the brief: the 10,000-row split on the unfiltered row_count, per-attempt upload keys, CAS-guarded state changes, complete_multipart before the done CAS, the one-active-export rule, the 24-hour bearer link, the 2-hour stale rule and the failure handling.
- Added a one-line 'What this is' paragraph and moved the out-of-scope items from the brief up to it, so a newcomer knows the boundaries before the steps.
- Added terms a newcomer needs and that were only implied: page view, row_count, Reader, Writer, job queue, attempt, final-failure handler, multipart upload, exports bucket, signed URL, export record, CAS and stale export. Each is defined in one plain line; the Reader and Writer are defined once, in the terms, instead of in a separate 'Shared parts' section.
- Added a short reason in each step, for example why the file is completed before the row is marked done, why each attempt has its own key, why the claim checks the attempt number, and why a 2-hour stale rule is safe.
- Merged the stale-check rules that were repeated in the click, claim, status and failure steps into one stale check, which the steps refer to by name.
- Replaced cross-references such as 'step 14' and 'step 6a/6b' with plain names. The '6a/6b' label was removed because it was a mistake; step 6 is one item.
- Moved the stale check before the insert in the click path, and stated that in step 4, so a stalled export cannot block a new click.
- Kept the open questions as the last section, and kept the failure table as one table, merging two rows about the upload window into one.
- Split the document into 'How it runs' and 'How to build and roll out', as the skill asks. The throughput gate, verification and formula-injection decision moved to the build section, and the formula-injection question stays open.
- Shortened several sentences so each step reads on its own, and dropped the wording that repeated the brief's rules without changing them.
- Did not change the plan's behaviour. The notice in the ignored-click path and the banner text match the answers given: rows written so far, with no total, and the last started attempt shown between attempts.

### Holes
- Q2: What is `enqueue` and the queue behind it? Which service runs the worker, and what triggers `report_export` handlers to start? (author: checked: jobs.py says enqueue(name, payload) queues a job, jobs run on the worker pool, and each worker runs one attempt at a time. unknown: what dispatches a queued job to a worker (push, poll, or a scheduler) and how long it can wait. The file does not say. The plan now says in the terms that a worker process runs the registered handler, and the open questions ask how a job starts and how long it can wait.)
