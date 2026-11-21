## Review of mr-01 (junior, author sonnet, natural)

Rounds: 4. Ended: teachback-correct.

### What changed
- Epoch now increments once (FAILING_OVER write); the final ACTIVE write keeps the epoch and checks run_id. Flowchart and text updated.
- Lease is now a separate key in the same store, renewed in one transaction that checks the record says A is active; explained how A learns it must stop.
- Demote is now defined as stopping A's PostgreSQL with a fast shutdown (dropped the read-only option) so in-flight transactions end; A's app is left alone.
- Added where the failover command runs: a host outside Region A, rerunnable from any host.
- Added what the command prints and that the override is a flag.
- Defined 'Retry, then escalate': the command retries about 3 times, then exits and on-call takes over.
- Added a short section on where the replay lag is recorded (the replica itself, read from B's database).
- Added Open questions: tuning values and record store product requirements (compare-and-set and multi-key transactions).
- Fence wait now runs until the lease key's expiry plus margin, instead of 15 s from the write, so it covers the watchdog's own counting from its last renewal (Q9).
- Flowchart and text state that the fence wait is a timer with no check that A stopped (Q10).
- Stated that A stopping itself during a store outage is intended, and that store outages and missed renewals page on-call (Q11).
- Added a section on what the command does at promote, scale-up and health check, including pg_is_in_recovery() and pg_promote() (Q12, Q16).
- Resume is now driven by the recorded step plus a check of real state, and real state wins on disagreement (Q13).
- Added an explicit resume flag. A FAILING_OVER record refuses a fresh run, and the pre-check box now allows FAILING_OVER when resuming (Q14).
- Replaced the undefined loss report with a printed summary of what the command can know, and said lost jobs cannot be listed (Q15).
- Added the health-check content of /healthz to the open questions (Q16).
- Added an 'App-to-database address' bullet under 'What the command does in each step': no app config change, because B's app already points at B's own database server (Q18).
- Added a 'DNS move' bullet under 'What the command does in each step': the DNS manager is the global traffic manager, the name points at A's load balancer before failover, the command repoints it at B's, and the call is idempotent (Q17).
- Added two open questions: confirm B's app points at B's own database server, and who owns the DNS name and which API call changes its target.
- Added a Pre-checks bullet saying the command does not check that A is down, and a matching bullet under Limits (Q24).
- Added a FAILING_OVER write bullet: what the compare-and-set compares and what happens when it fails, plus a failure table row (Q19).
- Added a Workers started bullet: the command waits for the worker group to reach its desired count before DNS moves. Updated the note under the flowchart, the trigger table and the failure table (Q21).
- Added a bullet that a resumed command re-reads the lease expiry and waits only for the remaining time, plus a failure table row for a crash during the fence wait (Q22).
- Added a clock-skew margin bullet (monotonic watchdog clock, store clock for the command, margin applied by the command only, proposed 5 s) and listed the proposal in Open questions (Q23).
- Made the watchdog count on its own monotonic clock, and made the command compare against the store's clock, so skew only comes from drift.
- Added a bullet and an open question that B takes no lease after cut-over, and that a B watchdog belongs to the failback plan (Q20).
- Reordered into the skill layout: summary (with how today's system works), terms, flowchart, numbered steps, failure handling, record store notes, limits, when A returns, open questions.
- Added a Terms section defining epoch, compare-and-set, write lease, watchdog, fencing, replay lag, traffic manager and the active-region record, one line each.
- Cut the separate 'What triggers each step' table and the 'What the command does in each step' list and merged them into one numbered 11-step list, each step with trigger, action, and failure handling. Removed the separate failure table; its rows now live in the step where they happen, with shared retry and resume rules in one 'Retries and resuming' section.
- Merged the 'Where the replay lag comes from' section into the replay lag term, and the duplicated fence/watchdog explanation from the record section into step 5 so it is said once.
- Moved the facts about today's setup (12 instances in A, 2 in B, replica, jobs table, Redis, DNS TTL) and the RPO/RTO targets into the summary, so no stated number was dropped.
- Kept the flowchart unchanged. Kept limits (lag check not an RPO guarantee, time budget, clock skew and paused process), the healthy-A failover consequence (now in step 3), A-returns steps and all open questions.
- Cut the 'Cut over' sessions bullet into step 11 and the 'does not confirm A is down' bullet into step 3. Dropped repeated restatements of the point of no return and of A staying fenced.

### Holes
- Q17: What is the "DNS manager" and what exactly does the command call to point the DNS name at B? Who owns that DNS name, and what does it point to before failover? (author: The DNS manager is the global traffic manager from the brief, which serves the one user-facing name with a 60 s TTL. Before failover the name points at A's regional load balancer (an inference from 'A serves all traffic'). The command calls the manager's API to point it at B's load balancer. The brief does not say who owns the name, which product it is or which API call is used, so I do not know. I added the first two facts to the step description and the unknowns to Open questions.)
