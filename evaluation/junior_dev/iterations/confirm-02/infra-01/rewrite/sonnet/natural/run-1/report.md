## Review of infra-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Reordered: summary, existing system, terms, shared rules, state record, steps 1-12 in order, then rollback paths, then open questions. Step 12 was previously stranded after the rollback paths.
- Replaced the 'Decisions this procedure makes' list with 'Rules that apply to several steps'; each rule now stated once (queueing, 5xx definition, metric outage, timers, migrations additive).
- Added a plain two-to-three sentence summary, an existing-system section and a terms list (target group, release id, /healthz, smoke tests, deploy lock, additive migration).
- Merged the three repeated abort descriptions into 'abort as in step 6' references; merged the manual rollback's duplicated text into 'same as automatic'.
- Cut the repeated explanation of why the live colour keeps serving in step 4 and the separate 'Never changes' bullet in the automatic rollback (folded into the migrations rule and a short clause).
- Added: 'no step is retried unless it says so', the manual rollback runs only when phase is watching or soaking, and an Open questions section (deregistration delay length, alert channel).
- Added the reason clause for migrations being additive and for ignoring low-traffic windows; removed pointers like 'see decisions above' in favour of named rules.
- Kept every number and limit from the first version: 4 instances, 3 passes, 10s checks, 10 minutes, 1% over 5 minutes, 15 and 30 minutes, 100-request minimum, 3 retries, 3 metric failures, 5-minute reaper, 60-second evaluation.

### Holes
- None.
