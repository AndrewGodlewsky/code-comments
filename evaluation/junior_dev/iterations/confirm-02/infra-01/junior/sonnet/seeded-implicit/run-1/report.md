## Review of infra-01 (junior, author sonnet, seeded-implicit)

Rounds: 5. Ended: teachback-correct.

### What changed
- Added a two-sentence intro and a terms line for blue/green, target group and test listener, because the bare checklist explained none of them.
- Defined the deploy lock as the CI concurrency group, with queue and release behaviour, so no new store or mechanism is needed.
- Said the LB listener is the only record of the live colour, so no new deploy state is stored.
- Added what the lint checks and that a lint or build failure stops the deploy before any change.
- Added the migration rules from the brief: additive only, run once before the new release, failure stops the deploy, never reversed.
- Added the health check and smoke test limits and the abort behaviour, and defined the test listener.
- Stated that the switch is a single repoint and that the 15-minute watch and the 30-minute rollback window are different.
- Added the teardown trigger and a recheck of the listener, so an engineer-started rollback that does not need the lock does not lead to the wrong colour being shut down.
- Added an Open questions section for the unknown /healthz and smoke suite contents and for invalid concurrent indexes.
- Lock step: stated the job holds the lock through the 30-minute wait and why (old colour is the rollback target), answering whether the next deploy is blocked.
- Health checks step: abort now stops the new instances and leaves the idle colour empty.
- Switch step: a failed repoint aborts the same way as the earlier aborts.
- Watch step: stated that the 15-minute and 30-minute clocks both start at the switch, that the 5xx rate comes from the LB metrics for the new target group, and what the job does after an automatic rollback (stop new instances, skip teardown, end failed, release lock).
- Rollback window step: described how the engineer-started rollback job picks the target and why it needs no lock, and that it refuses once the old colour is shut down.
- Migrations step: the runner skips already-applied migrations, and the lint checks only this release's new ones.
- Open questions: added that the 5xx metric query and the migration tool are not chosen.
- Deploy step: first stop leftover instances in the idle target group (answers Q21 and Q19 cleanup).
- Watch step: check once a minute starting at 5 minutes so each covers a full window; unreadable metrics trigger rollback; failed job is the alert (Q16, Q17).
- Keep-old-colour step: the listener recheck also happens at each 5xx check, and a manual rollback makes the job stop the new instances, skip teardown, end failed and release the lock (Q18).
- Teardown step: says what is stopped and that both target groups stay, the old one becoming the idle colour (Q20).
- Lock step: also released on cancellation; added a short note on what happens if the job dies or is cancelled (Q19).
- Open questions: added whether CI already notifies on failed deploy jobs.
- Smoke test step: starts only after all 4 instances are healthy; if the 10 minutes run out mid-run the job stops the run and aborts.
- Watch step: automatic rollback repoints only if the listener still points at the new colour, otherwise it leaves the listener alone (fixes a race with the manual rollback).
- Keep-old-colour step: manual rollback is given the new colour as input and repoints only if the listener still points at it, so simultaneous rollbacks both end on the old colour.
- Keep-old-colour step: stated that nothing watches 5xx automatically between minutes 15 and 30.
- Job-dies paragraph: stated the cost that a cancelled job after the switch lets the next deploy stop the old colour, losing the rollback target, and that the listener alone cannot show this.
- Lock step: added a minimum CI job timeout of 60 minutes, because the job holds the whole deploy including the 30-minute wait (Q26).
- Closing paragraph: said that hitting the CI maximum duration or losing the runner is the same as the job dying (Q26).
- Health-check step: stopping the new instances waits for completion; if stopping fails the job still ends as failed and the next deploy clears leftovers (Q27).
- Watch step: defined the 5xx rate as the share of requests, with no minimum count and zero requests counting as 0% (Q28).
- Migrations step: said who runs them, against which database, and that only the CI job timeout limits them, with a timeout treated as a failed migration (Q29).
- Switch step: on a failed or unclear repoint, re-read the listener, abort if old and continue if new (Q30).
- Open questions: added that the real CI duration limits are not known.
- Merged the 12 bare checklist lines plus long notes into a numbered checklist with the same step names, numbered and in order; each step now states trigger, effect and failure handling.
- Added a leading summary (how it works today, main flow, why) and a Terms section defining blue/green, target group, public and test listener, old/new colour, lock and shared database.
- Split Health checks and Smoke tests so the shared 10-minute limit and the abort handling sit in one place (step 7) and step 5 says when the clock starts.
- Merged the automatic and manual rollback rules, and the post-rollback cleanup (stop new instances, skip teardown, fail job, release lock), into one Rollback section instead of repeating them in steps 9 and 10.
- Added a failure table, and kept the job-dies paragraph and the lost rollback target cost.
- Removed repeated statements: the lock-held-through-wait reason, the 'stop the new instances waits' rule and the 15/30-minute clocks are each said once.
- Kept all brief facts: additive-only migrations and later drops, 3 passes at 10-second intervals, 10-minute limit, single-step switch, 1% over 5 minutes, 15-minute watch, 30-minute old colour, 60-minute CI timeout, no minimum request count, open questions.
- Added the migration lint tool to the open questions, since it is not chosen.
- Cut nothing the first version stated; it mainly named steps, and every step name is retained.

### Holes
- Q5: What do the health checks test, and what happens if one of the 4 instances never becomes healthy? (author: What /healthz tests inside the service is not known. Per the brief, all 4 instances must pass 3 times in a row (checks every 10 seconds). If one never gets healthy, the 10-minute limit passes and the deploy aborts without touching the public listener.)
