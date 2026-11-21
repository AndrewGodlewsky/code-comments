## Review of infra-01 (junior, author sonnet, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Added first-ever-deploy handling to Terms and step 3, because no tags exist then.
- Defined the start request in step 6 as a call to the platform's instance launcher with the artifact SHA.
- Clarified in step 4 that the additive check is what protects the old release.
- Stated in Terms and step 8 that the health gate and smoke suite share the 10-minute budget.
- Defined a breach as a single evaluation above 1%, and said where the rate comes from in step 11.
- Spelled out in step 11 how a retried run keeps the lock and picks its resume step from tags and the listener.
- Fixed step 13, step 14 and the rollback job so an engineer rollback during the hold sets rolled_back tags and ends the run as rolled back.
- Added a short 'When a page arrives' section and an Open questions section for unknown launcher, smoke suite, pager recipients and lock-on-retry.
- Terms: new colour is always the opposite of the listener, and tags on the idle colour are ignored in step 3 and overwritten in step 6 (answers Q9, Q10, Q15, Q16).
- Terms and step 7: the pipeline job runs health checks from the runner, and a pass is HTTP 200 within 5 seconds.
- Step 3: now says only the live group's tags are checked, and the new colour's tags are ignored.
- Step 5: states the assumed advisory-lock behaviour, so a dead run does not block the next.
- Step 6: says tags are overwritten, whatever they were.
- Step 9: runs a fresh /healthz check instead of relying on step 7.
- Step 10: notes the conditional update is assumed to exist, and says what to do when the condition fails (stop and page).
- Abort and rollback job: say what the failed colour's tag and instance count are afterwards.
- Step 14: removed the vague phrase 'marks the tags final'.
- Tags table: lists every status value used, including old, failed and rolled_back.
- Open questions: added three assumptions (migration lock release, runner network access, conditional listener update).
- Step 3: re-check instance count after stopping strays; deploy stops and pages if they will not stop (Q17).
- Terms: spelled out which 5xx and total counts are read and that only datapoints from T0 onward count (Q18).
- Abort: page now lists applied migrations and says the database is ahead of the live release (Q19).
- Step 9: when the listener has moved, new instances are left running, the page says so, and no deploy starts until tags agree (Q20).
- Step 10: read the listener before each retry, treat a listener on the new group as success, and Abort only when it is confirmed on the old group; Abort trigger now names step 10 (Q21).
- Rollback after shutdown: reuses the published artifact and goes through the same gates (Q22).
- Removed the unused retire_at tag from step 10 and noted that step 13 uses only switched_at (Q23).
- Step 13 trigger reworded to 30 minutes since switched_at.
- Step 6 and the state table: the old group's tags stay `live` until step 10, and `old` is only a human label that nothing reads (Q24).
- Step 11: replaced the run-died rule with a clear decision list, adding the case where the run died between the switch and writing `switched_at` (write it as now) and the case where the listener is still on the old group (restart from step 3) (Q25).
- 11a and the rollback job: defined what the loser does when 11a and an engineer rollback race (Q26).
- Step 1: said that a replaced waiting run is reported cancelled and that the newest merge contains the earlier ones (Q27).
- Step 5: said the next deploy sees only migrations not yet recorded as applied (Q28).
- Rollback after shutdown: said step 4 finds nothing pending for the old release (Q29).
- Added an opening summary: how the service works today (two colours, one listener, shared database), the main flow, and why it is shaped that way. Folded the first-version intro into it.
- Added definitions for newcomer terms the junior stumbled on: listener, target group, migration, tags (with the status values, noting `old` is human-only), T0, the deadline (shared budget), health check (HTTP 200 within 5s, called directly), breach.
- Merged the old 'Terms and decisions' and 'Where deploy state is kept' into one Terms list plus a short 'Rules that apply to the whole deploy' section (one deploy at a time, listener is truth, idle tags ignored, additive migrations, state table). Each rule now appears once.
- Moved the run-death resume logic out of step 11 into a single 'If a run dies' section, and made steps 12 and the failure notes point to it instead of repeating it.
- Moved the first-deploy tagging, the 'new colour is normally shut down' note and the 'old colour is shut down after 30 minutes' note to the steps where they apply (3 and 13). Removed the duplicate statement of the 5xx datapoint rule from several places.
- Trimmed repeated explanations: the 'Fails' wording, the pre-switch no-traffic reasoning, the 5xx window description, the repeated 'migrations never reversed' notes, and the second telling of the lock reasoning.
- Dropped the remark that the 10-minute clock starts at the start request as a separate term; it is now in the 'deadline' term and step 6.
- Kept every requirement, number and rule from the brief and the first version: 4 instances per colour, 3 consecutive passes every 10s, 10-minute deadline, one-step switch, 15-minute watch with 1% over 5-minute windows, 30-minute hold, rollback never reverses migrations, rollback jobs, open-for-you-to-confirm items, and all open questions.
- Kept the state-kept-where table and the 'no separate deploy-state table' reasoning, merged into the rules section.
- Did not add anything about details no question needed (exact launcher tool, smoke suite contents, concurrency-group internals); these stay as open questions.

### Holes
- Q2: In step 6, what actually starts the 4 instances and where does the new release's code come from? Is it the artifact from step 2 pulled onto instances by some tool, and what is the 'start request' that begins the 10-minute clock? (author: The pipeline sends a start request, an API call to the platform's instance launcher naming the step 2 artifact SHA; that call is what starts the 10-minute clock. Which launcher tool and how it pulls the artifact is not known, so it is listed under Open questions.)
- Q8: Who gets paged, and who is 'the owner'? What does the engineer on the receiving end do first when a page arrives with the listener and tags in a mixed state? (author: I do not know who is paged or who the owner is; this is listed under Open questions. On a page the engineer first reads the listener, treats it as the truth, and fixes the tags to match before any new deploy. Added a short 'When a page arrives' section.)
- Q11: What does the 'migration tool' do when it takes its database lock in step 5, and what happens if a run is aborted or dies mid step 5 while holding that lock? Does the next run get blocked? (author: The migration tool is not chosen. I assume it uses a session-scoped PostgreSQL advisory lock to stop two runs migrating at once. Such a lock is released when the connection ends, so a run that dies or is aborted mid step 5 does not block the next run. This is an assumption, not verified, so it is listed under Open questions.)
- Q14: In step 10, how does the listener update stay 'conditional on the listener still pointing at the old one'? Is that a feature of the load balancer API, and what does the run do if the condition fails? (author: I assume the load balancer API can make the listener update conditional on the current target. I have not verified that, so it is listed under Open questions. If the condition fails, the listener has moved by itself, and the run stops and pages without touching anything else, as in step 9. Added to step 10.)
