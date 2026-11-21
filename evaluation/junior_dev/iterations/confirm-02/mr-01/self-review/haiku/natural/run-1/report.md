## Review of mr-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a short orientation paragraph before the flowchart so a reader new to the system knows what A, B and the standby are.
- Flowchart step 4: replaced "DNS stays on A" with "DNS not moved", because A is already down or fenced, so "stays on A" was misleading.
- Flowchart step 3: the compare-and-set now also requires the lease to have expired, because A may renew during the wait. The original did not re-check this.
- Flowchart step 2: the operator now sees the frozen lag and the LSN gap before the override decision, as the notes already said. The original only logged them after the override.
- Flowchart step 5: added the reaper's requeue path to the max-attempts check, and added the backoff loop back to claiming. The original only checked attempts on errors, so a job that crashed repeatedly would never be failed. The owner should confirm this logic change.
- Notes on the data-loss gate: the original said to treat the "larger of the two" numbers as exposure, but one is seconds and the other is bytes. The notes now say the operator reads both, and that the plan owner should set a byte threshold.
- Notes: defined the terms a new reader would not know (lease, fencing, compare-and-set, epoch, timeline, LSN, replay lag, base backup, pg_rewind, reaper, backoff, clock skew, idempotency key, TTL).
- Notes on idempotency: softened "a retry cannot repeat an external effect" to say the external system must honour the key, since the plan cannot guarantee that alone.
- Notes on triggers: clarified that steps 3 to 5 run automatically once the command has started them, so only the start is manual.
- Notes on jobs mid-run: reworded the three outcomes so each says what B's copy of the jobs table shows and what happens next.
- Opening paragraph now states B's actual standby setup: 2 web servers kept running, workers scaled to zero.
- Added a short Terms list at the top of Notes to define replica, replay lag, LSN, timeline, promote, fencing, lease, witness, idempotency key and reaper.
- Flowchart gate fixed to match the notes: both the frozen lag and the LSN gap are shown on every path, and the run proceeds without an override only when lag is 30 s or less and the gap is under the byte threshold. Previously the LSN gap appeared only on the over-30 s branch, although the notes say a large gap matters even under 30 s.
- Fencing made explicit in step 3: the wait node now says A's own fencing agent has made A read-only by the time the wait ends.
- Fixed a contradiction on the epoch: the notes said the epoch was 'set to match' the Postgres timeline while also saying it rises by one. The record now stores the epoch and the new primary's timeline number as separate fields, and an old primary compares both.
- Rewrote dense sentences in plain language, including the fencing residual risk, the data-loss gate, the job-run cases and the RTO budget, and added a note that the lease wait is about one minute with the example 30 s lease.
- Kept the flowchart structure, the five steps, the open items and all stated values (10 s probes, 2-of-3 rule, 30 s lag limit, 60 s TTL, 15 min RTO) unchanged.
- Added a plain-language opening that says the design goal is no two writable databases, and points to the residual risk, instead of stating the goal as an absolute.
- Expanded the terms list with definitions for warm standby, WAL, PostgreSQL, timeline, compare-and-set, RPO, RTO and TTL, and defined LSN gap in terms of the two log positions it compares.
- Defined 'claim' in the jobs section and explained that a claim sets status running, with its lock and attempt count.
- Explained that the compare-and-set fails if the record changed after the command read it, rather than using the bare term.
- Reworded flowchart labels to shorter plain phrases (for example 'probes see 3 failures in a row', 'Wait for A's lease to expire, plus a clock-skew margin'), with no change to the steps, branches or triggers.
- Replaced 'Nothing is promoted' style phrasing in the flowchart and notes with clearer wording, and explained what 'read-only' and 'fencing agent' mean.
- Explained that the unreachable-A problem means the LSN gap needs A's last known position, which the original did not say where to get. Added this as an open item with one suggested option (A reports it with each lease renewal), marked as a suggestion rather than a decision.
- Added an open item to set the LSN gap byte threshold, which the notes said the plan owner must set but the open items did not list.
- Clarified in the returning-A section that pg_rewind resynchronises only the differing parts and that changes after the split point are discarded.
- Kept the flowchart structure, the five steps, the record fields, the RTO budget and the document layout unchanged.

### Holes
- None.
