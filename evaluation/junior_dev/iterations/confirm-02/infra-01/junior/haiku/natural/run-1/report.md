## Review of infra-01 (junior, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Step 1: removed the 'idle colour has no hold running' check, because the lock is held through the hold and the check was redundant.
- Step 2: now scales down leftover instances on the idle colour (from an aborted deploy) before the check, instead of requiring zero running instances. Answers Q8.
- Step 4: set statement_timeout to 10 minutes, which the first version left unspecified.
- Step 7: states that the smoke suite runs from the CI runner through the internal test path, and that a timeout counts as failure.
- Step 9: added handling for a failed state write after the switch.
- Step 11: corrected the reason the new colour stays live (the listener still forwards to it, not because it is the only reachable colour). Added status holding after a successful rollback, and handling for an unhealthy old colour after rollback.
- Hold rule: hold_until is set once at the forward switch and a rollback does not move it. Removed the 'whichever direction the last switch went' wording, which conflicted with it. Answers Q7.
- Step 12: manual rollback allowed only in holding status, and it refuses to return to rolled_back_from. Answers Q7.
- Step 13: previous_release_digest is no longer overwritten after a rollback. The first version would have made the breached release the rollback target. Also added previous_release_sha.
- Added the rolled_back_from and previous_release_sha fields to the state record.
- Rollback after shutdown: now an engineer-started deploy that uses the stored digest and skips the build in step 3. The first version said it runs steps 1 to 14 but did not say how it starts or where its image comes from. Also stops if there is no previous release.
- Step 14 and step 8: queued deploy starts by running step 1 for queued_sha. Answers Q1 and Q2.
- Merged the separate Decisions section into the terms, the state record and the steps, so each fact appears once. Added a short summary, a terms list, and a 'How the run is driven' section that says which job runs which steps (Q1).
- Open questions section added for the holes the questions exposed: compute platform, smoke suite contents, metric source, index build timeout, untested old colour, watch outage, stuck hold, rollback approvers.
- Terms: added Deploy ID, so the reader knows what deploy_id is (Q13).
- How the run is driven: the watch runs until step 14 finishes, not only until the hold ends. After a rollback the 5xx watch stops but the job runs on for step 13. The job does nothing in statuses it has no step for (Q10, Q11).
- How the run is driven: the pipeline run writes heartbeat_at at each step start, and the stale-lock alert is defined as lock held with heartbeat_at over 15 minutes old (Q16).
- Step 5: instance tags now include image_digest, the platform's role in adding instances to the colour's target group is stated as an assumption, and the tags are named as the record of each colour's release (Q9, Q15).
- Step 8 and step 14: the compare-and-set that clears the lock also takes and clears queued_sha, and the queued SHA is started as a new pipeline run with its own deploy_id. Before, step 14 cleared queued_sha after starting the run (Q13).
- Step 10: 5xx evaluation runs only while status is watching (Q10).
- Step 11: the status change is a compare-and-set from watching. A failed listener update leaves the lock held and the watch idle until an engineer acts (Q14).
- Step 12: moves status to rolling_back from holding before repointing, so it cannot overlap with step 13 (Q12).
- Step 13: moves status to shut_down by compare-and-set from holding before scaling down, so step 12 and step 13 cannot both act. Release digest and sha are read from the non-live colour's instance tags, before its instances stop. A failed scale-down keeps status shut_down, not holding, because the shut-down decision has already been made (Q12, Q15).
- Open questions: added the crashed-run case, the unresolved way to clear rollback_failed, and the ordering race between a new merge and a queued SHA (Q13, Q14, Q16).
- CUT: the first version's 'Decisions made' list is gone. Its facts now sit in the Rules, the state record, the terms and the steps, each stated once.
- CUT: repeated statements. The lock-held-through-hold rule appears once, in Rules. The 'migrations stay applied' point is stated once, in step 8, with its reason. The 'rollback repoints at once' point is stated in step 11 only. The rollback-after-shutdown section lists only the three changes, not the steps again.
- CUT: the first version's line that a suite failure 'means the deadline's condition was not met'. It restated step 7.
- MERGED: the step 12 failure handling now points back to step 11 in one line. The statuses are one list with a one-line meaning each. The How-the-run-is-driven bullets cover the watch job, heartbeats and the stale-lock alert together.
- ADDED: the brief's migration rule (additive only: new tables, nullable columns, indexes; drops and renames wait for a later release). The draft had only the step 3 lint.
- ADDED: the hold rule (no deploy writes to a colour before its hold ends; hold_until is set once and never moved by a rollback; the non-live colour is shut down whichever direction the last switch went).
- ADDED: the 5xx rate formula and the rule that rollback does not wait for the old colour's health check. Both were in the first version and were missing from the draft.
- ADDED: short definitions for T0, the watch job, heartbeat, SHA, 5xx rate, listener forward action, and the statuses. These are names a newcomer would not know.
- DECIDED (not in the brief): step 6 keeps its pass counts in the pipeline run only, not in the state record. Step 7 writes its result to the CI run log.
- DECIDED (not in the brief): if the rollback deploy's previous_release_digest is empty, it releases the lock as it stops before step 2. The draft left the lock held, which would block all later deploys.
- KEPT: all 14 steps with their trigger, action, keeps and failure lines; all 19 state fields; all 9 statuses; the T0 + 10 minute deadline; the 10-second, 3-pass health rule; the 1% and 100-response breach rule; and all 11 open questions.

### Holes
- Q9: The listener always forwards to exactly one target group, and the idle colour has 4 instances in its own group. What puts the new instances into the idle colour's target group, so the listener can send traffic to them at step 9? Is that automatic when desired count is 4, or a separate action? (author: The brief does not name the compute platform, so I do not know how a started instance joins its colour's target group. The plan assumes the platform does this when the desired count is set. I stated that assumption in step 5 and kept it in Open questions.)
- Q14: If the status is rollback_failed or migration_failed, who clears the lock or moves the deploy on? Step 11 sets rollback_failed but does not say the lock is released, and step 14 only runs after step 13. What state is the system in and how do deploys resume? (author: migration_failed releases the lock in step 4, so the next merge's step 1 can run. rollback_failed does not release the lock. The new colour stays live, and the watch job does nothing. The brief does not say how an engineer clears this state or hands the deploy back to the watch, so that is in Open questions. I changed step 11 to state the lock and the watch's behaviour.)
