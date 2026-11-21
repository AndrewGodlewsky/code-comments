## Review of rt-01 (junior, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Replaced the vague 'clients keep a presence store' with the Redis state layout: the keys, their types, who writes each one and who removes it (Q1).
- Added the ordering rule for open: subscribe, write, publish join, then read the snapshot, so nobody is missed between snapshot and live updates. Snapshot now includes each tab's last cursor, so idle users show (Q2).
- Named one pub/sub channel per document and explained that nodes forward to their own local sockets only (Q3).
- Defined the 50 ms throttle (client sends, server drops silently) and the seq number, and why each is needed (Q4).
- Stated that transformPosition runs in the client editor, and wrote the step-by-step revision rules for hold, transform, drop and no backwards jumps (Q5).
- Replaced the ambiguous 'ping/refresh' with the existing WebSocket liveness check and a per-node heartbeat key with a 30 s TTL refreshed every 10 s (Q6).
- Specified the sweep: who runs it, how a dead node is detected, that only one node publishes each leave, and the 40 s worst case against the 45 s limit. Fixed the crash arrow label (Q7).
- Replaced 'dedupe tabs on the client' with server-side per-user join and leave, per-tab carets and the rule for a closing tab (Q8).
- Added a failure table and an open questions section for the Redis outage, failover and Postgres-table cases, which the first version did not cover.
- Kept the brief's fixed requirements in the file: per-user presence, snapshot on join, 50 ms cursor rate, ephemeral cursors, revisions, no backwards jumps, 2 s clean leave, 45 s crash cleanup, and no change to the edit path or load balancer. The file is longer than the first version because those requirements were missing from it.
- Step 1.2 (open): the join decision is now one script that adds the tab and returns the count before, so two tabs opening on different nodes at once cannot both see the first tab (Q9).
- Step 4 (clean leave) and step 5 (sweep) now share one leave script that acts only when the tab is still present, and returns whether the user has tabs left. This makes the sweeper's last-tab decision and the no-double-publish rule explicit (Q11).
- Step 5.3: the sweeper's publish needs no subscription, which is stated in the step (Q12).
- Client section: added rules for join, leave with userGone true and false, and cursors from unknown connIds. Cursor messages now carry connId and userId, and the snapshot carries each tab's seq (Q13).
- Step 3 (heartbeat): a failed heartbeat write now closes all the node's sockets. This replaces the former open question about it, and the Redis-outage failure row now matches (Q14).
- Step 2.1: the throttle timestamp is kept in node memory per connection, not in Redis. Step 2.2 now says the cursor is written before it is published, and the failure table says what happens if the publish fails (Q15).
- Step 3: added that a node writes its heartbeat before it adds its id to nodes, so a starting node cannot be swept.
- Merged the tab rules into the client section and removed the repeated leave explanation. Moved the Build section out of the flow, into its own section at the end.
- Added open questions: lost join or leave publishes leave other clients with a wrong list until they reopen, and drawn carets may not move with later edits. Both are unknown and the plan does not answer them.
- Diagram: messages now name the join and leave scripts, the cursor carries connId and userId, and the sweeper removes the dead node from nodes.
- Heartbeat step and failure table: a node whose heartbeat write fails now closes its sockets and exits, so its key expires and a sweep removes its records (Q16).
- Terms: added nodeId, with a new random id on every start (Q17). Added the definitions of ping/pong, heartbeat, script and transformPosition/HistoryGone so each term is defined once.
- Clean leave: added step 4, which unsubscribes from presence:<docId> when the node's last local socket on that document closes, and resubscribes at the next open (Q18).
- Node crash: added the reconnect case, where a user who comes back on another node before the sweep stays listed and only the old caret is removed on the sweep (Q19).
- Restart row in the failure table now says where the tabs' leaves go and that the restarted node gets a new nodeId.
- Layout: summary and terms now sit just before the diagram, and the diagram notes just after it. The state table and steps follow. Client rules have their own section. Build and rollout are in their own section, separate from how the system runs.
- Failure table is now keyed by step. Each step's failure handling is in one place, instead of repeated in the steps.
- Wording: each step names its trigger and the part that keeps its data. The transform repeat now refers to the transform itself, not to another numbered item. Facts from the first version are all kept, including the 2 s leave, 45 s limit, 50 ms throttle, 10 s and 30 s intervals, no Postgres or document-service path for cursors, and the unchanged edit path and load balancer.
- Rewrote the whole file once for a newcomer, in the required order: summary, terms, diagram, diagram notes, state table, how the system runs (steps, client rules, failures), how it is built, open questions.
- Summary: now says how the Postgres list works today (30 s polling, nightly cleanup) and what replaces it, in three sentences.
- Terms: added definitions the junior needed but the first version lacked: local socket, channel and publish/subscribe, script, caret, snapshot, sweep, HistoryGone, appliedRev, nodeId as new on each start. Each is one line.
- Corrected a first-version claim: 'Entries have a TTL' is now precise. Only node:<nodeId> has a TTL; presence records have none, so a dead node's records wait for a sweep.
- Corrected the first-version 'Dedupe tabs on the client' note to server-side de-duplication (per-user joins and leaves only at first and last tab), as the answers decided. The client still keeps one caret per user.
- Merged duplicate content: the client join/leave/cursor rules and the tab rule each appear once, in one section; the failure handling that the steps repeated is now only in the failure table.
- Removed the step-4 line 'the node keeps no data of its own here', which was confusing; step 4 now states what it removes.
- Step 3 now says why a failed heartbeat write means exit (a node that kept running would never look dead), and why the heartbeat is written before the id joins nodes at start.
- Step 2 now states that the 50 ms throttle timestamp lives in memory, with the reason (one node per connection; restart resets it), and that the cursor write happens before the publish.
- Step 5 now states the 45 s limit is a requirement of this change and that the 40 s worst case fits inside it, and adds that other clients see the reconnected user's new caret after the next move.
- Diagram kept unchanged in its sequence. Notes moved after the diagram and now also say join/leave are per user, not per tab.
- The state table is kept in full, placed before the steps, with the TTL note under it. Stated facts kept: every row, every step, the 2 s leave, the 50 ms throttle, the 10 s ping and 20 s pong limit, the 30 s TTL, the 10 s sweep, the restart and reconnect behaviour, and all four open questions. Nothing from the brief or first version was cut.
- Length: the file is longer than 1.5 times the first version, because the brief's fixed requirements and the answered questions each had to keep their facts. Repetition was removed wherever possible.

### Holes
- None.
