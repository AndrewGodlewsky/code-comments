## Review of dp-01 (junior-v6, author sonnet, seeded-implicit)

Rounds: 4. Ended: teachback-correct.

### What changed
- Rewrote the file in the skill layout: summary paragraph, terms, diagram, numbered steps, failure table, build/rollout section, open questions.
- Expanded the Mermaid diagram into a real flow with edges for the watermark, replica, etl_runs, retries, paging, the 06:00 check, alerts and reconciliation.
- Decided and stated that only the Merge transaction advances the watermark, and that it commits together with the fact_orders upsert.
- Stated that stg_orders is emptied at the start of each attempt and deduplicated by highest updated_at per order_id.
- Defined the merge rule: overwrite only when staged updated_at is greater, and is_deleted = (deleted_at is not null).
- Spelled out retry as whole-job, 3 attempts total, 15 min apart, then page on-call, and separated paging from the 06:00 staleness alert.
- Defined etl_runs and who writes and reads it.
- Specified reconciliation detail: count and checksum per creation day for 30 days, reload mismatched days through staging with the same merge, no change to the watermark.
- Restored brief facts that the first version dropped: read only from replica, no write access to the app database, 90-minute bulk-import reason, deleted orders kept, dashboards never see a half-loaded night.
- Added decisions marked as mine: reconciliation failure is alerted and not retried until next Sunday, and is skipped if Sunday's load never commits.
- Added Open questions: paging tool and reconciliation retry.
- Reconciliation now stages into its own table stg_recon instead of sharing stg_orders, so it can never collide with a nightly attempt (answers Q12); added stg_recon to terms, diagram, step 6 and build list.
- Step 6 and the diagram now say the Sunday nightly Merge commit starts the reconciliation, with no separate schedule (answers Q11).
- Defined the night value in etl_runs as the UTC date of the 02:00 start, shared by all attempts, and made the 06:00 check look up that night (answers Q13).
- Step 5 and the failure table now state that the 06:00 check does not stop anything and a running or waiting attempt may still commit later (answers Q13).
- Added a Scheduler term: it owns starting attempts, retries, and writing running/failed etl_runs rows for attempts the job cannot log itself.
- Step 1: each attempt, including retries, gets its own etl_runs row with status running, written by the scheduler.
- Step 4 rewritten: the scheduler detects failures (logged by the job, or crash/non-zero exit/timeout seen by the scheduler), marks the row failed, waits 15 minutes, starts a new attempt, and pages after the third failure.
- Diagram: added a crash/exit/timeout node feeding the failed-attempt node, and labelled the retry edge as scheduler-started.
- Failure table: added a row for process crash, kill, hang or never starting; retry row now says the scheduler does it.
- Defined etl_runs status values (running, success, failed); added the unset attempt time limit as an open question; build step 3 mentions crash and timeout detection.
- Step 6 and the diagram: the scheduler, not Merge or the job, launches the Sunday reconciliation, writes its running row, applies the time limit and marks it failed on crash or hang, so one component owns every job process.
- Step 5 and diagram: the 06:00 check reads only kind nightly rows, so reconciliation rows cannot mask a missing nightly load.
- Step 1 now states the nightly row has kind nightly.
- Reconciliation failure: the scheduler posts to #data-alerts, in step 6, the failure table and the diagram; there is no retry or paging.
- Scheduler term widened to cover reconciliation and the failure alert; open question notes reconciliation may need a longer time limit.
- Rewrote the opening paragraph to say there is no warehouse copy today, then give the flow end to end and why it is shaped that way (one transaction, so dashboards never see a half-load).
- Merged the Start and Extract answers into the steps: the scheduler hands over nothing, so Extract finds its own starting point and the mark lives in one place.
- Added to the terms that the stored high-water mark never moves back (only the query subtracts 2 hours), and that the scheduler also pages on-call.
- Put reasons next to the parts they explain: emptying stg_orders so a retry sees no leftovers, only Merge moving the mark, the scheduler owning retry timing and attempt count.
- Restructured step 6 (Sunday reconciliation) into start, compare, reload, why it is safe and failure sub-points, and stated that it does not page on-call.
- Renamed the 'Steps' section 'How it runs' to keep it apart from the build and rollout section.
- Dropped the separate statement that ties are impossible to distinguish and kept only one clause on exact ties. Removed no stated brief facts: 02:00 UTC, replica-only reads, 90-minute and 2-hour numbers, 15-minute and 3-attempt retry, 06:00 check, 30-day checksum reconciliation and is_deleted were all kept.
- Left out the rare-edge-case detail of exact formats, since no question asked for it; the diagram and failure table are unchanged.

### Holes
- None.
