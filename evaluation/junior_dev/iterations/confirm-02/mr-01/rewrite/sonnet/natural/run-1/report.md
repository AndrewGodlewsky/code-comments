## Review of mr-01 (rewrite, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Restructured into the skill's order: summary, how it works today, targets and fixed rules, terms, flowchart, steps, shared failures, jobs, A returns, RTO budget, not covered, rollout, open questions.
- Added a short 'how the system works today' section (12 and 2 instances, Postgres replica, jobs table, Redis, 60 s DNS) because the first version assumed it.
- Added a 'Targets and fixed rules' section so every brief requirement (RPO, RTO, probe rule, no auto-promotion, ordering, sign-in, no failback) is stated once.
- Added a Terms section defining replay lag, fencing, active-region record, epoch, compare-and-set, lease, watchdog and point of no return in one line each.
- Merged the 'Decisions this plan makes' list, the trigger table and the failure table into one numbered list of steps. Each step now gives its trigger, what it does and what it does on failure.
- Cut the repeated explanation of the lease and fencing, the lag-gate caveat and the requeue, which each appeared in two or three places. Each now appears once.
- Kept the flowchart, with one fix: the app scale-up now branches from the PROMOTED node, to match the trigger table. The requeue no longer appears to gate it.
- Kept the abort, two-operator, killed-command and no-way-back-after-PROMOTED rules in one short list of failures that apply to every step.
- Moved 'A returns' out of the record section into its own short section. Moved drills into a separate Rollout section, apart from how the system runs.
- Added an open-questions section: idempotency keys, the untimed scale-up estimate and the 15 s margin as a judgment rather than a measurement.

### Holes
- None.
