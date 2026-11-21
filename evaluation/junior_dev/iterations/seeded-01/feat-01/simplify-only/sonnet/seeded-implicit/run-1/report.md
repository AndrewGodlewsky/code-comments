## Review of feat-01 (simplify-only, author sonnet, seeded-implicit)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote into the newcomer layout: summary and how the page works today, terms, numbered steps, failure table, build order, open questions
- Merged the separate 'prevent duplicates' and 'errors' items into the steps they belong to (click, job, final failure) and one failure table
- Merged 'cleanup is handled by the bucket lifecycle rule' into the email/done step
- Gave every step the same four parts: what starts it, what it does, where data is kept, what happens on failure
- Replaced the vague 'prevent duplicate exports' with one mechanism: a unique rule on user and report for queued/running
- Used one simple failure handling: abort upload and rely on queue retries, no locks, leases or takeover
- Defined the large-report threshold as unfiltered row_count and the state fields once in the terms
- Moved rollout into its own short section, separate from how the system runs
- Cut details the plan does not need: exact column names, template parameters, exact batch size
- Added open questions for timeout fit, missing email templates, permission recheck, mid-export nightly rebuild, and stuck record if final-failure handler crashes

### Holes
- None.
