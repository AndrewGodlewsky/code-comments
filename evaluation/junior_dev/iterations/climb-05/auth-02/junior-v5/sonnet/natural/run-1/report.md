## Review of auth-02 (junior-v5, author sonnet, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Assumptions: said the store product and identity mechanism are not named in the brief, and that step 1 records them and step 2 verifies them (Q1).
- Added an open question on what happens to the order after a final provider error, owned by the orders-api team (Q6).
- Step 1: also record the store product and identity mechanism (Q1).
- Step 4: corrected values reach running pods within 5 minutes (Q2).
- Step 6: spelled out the order of PR approval, staging, merge and prod deploy for both pipeline cases (Q7).
- Step 7: starts after the merge, explained why old pods still hold the old keys (their image has its own YAML copy), and gave concrete stop criteria for the first-pod check (Q4, Q8).
- Step 8: said how to query the secrets_refreshed line and match it to pods (Q5).
- Step 14: fetch the latest version (Q2).
- Step 15: named /healthz as the readiness probe and said that a server not yet listening counts as not ready (Q3).
- Step 16: the provider error goes back to the caller, with a pointer to the open question (Q6).
- Step 17: secrets_refreshed now carries the pod name, with an example line (Q5).
- Step 7: added who decides a rollback and what it does (redeploy previous image under the same rolling rules).
- Step 1 and step 8 check 3: record per provider where old-key last-used is shown and its lag; margin must exceed it. Added matching open question.
- Step 15: added terms for Secret/reveal(), the secrets provider and the snapshot, and who owns the refresher thread.
- Step 16: a forced re-read updates the shared snapshot for all requests; the timer is unaffected.
- Step 17: partial failure handling spelled out; the refreshed line shows the older version for a failed secret.
- Step 9: defined pre-migration images and why running or rescheduled pods are unaffected.
- Steps 2, 3, 6: staging uses sandbox keys, has its own identity limited to staging/*, and old-image staging pods keep old keys until replaced.
- Step 1: also record per provider whether rejected attempts on a revoked or suspended key are visible with the caller, because step 10 depends on it.
- Step 7: one clause saying old pods never call the store, so a store outage affects only new pods.
- Step 8 check 2: expected version is the store's latest version id at check time, matching the ticket; a pod with a stale latest line fails; added a line on how the three checks cover each other.
- Step 10: said what to watch after suspension and how to tell a missed caller from another cause.
- Step 14: the pod authenticates with the platform identity, and failing to get it follows the same retry path.
- Step 16: rewrote the 401/403 handling as numbered cases, adding a retry from the current snapshot with no store call and the explicit 30-second skip behavior.
- Reordered to the skill layout: one summary paragraph (starting with how config works today), then terms, then steps, then failure table, then open questions.
- Split into Part 1 (runtime) and Part 2 (rollout) and put runtime first; renumbered both parts so each step is self-contained, and replaced most cross-references to step numbers with named references.
- Added a Terms section: secret store, version id, path, identity, APP_ENV, Secret, secrets provider, snapshot, readiness probe, security on-call.
- Merged the assumptions block and the three separate open-question sections; moved all open questions to the end and added the store product/identity question as an open item.
- Merged old steps 13, 14, 15 and 18 into tighter runtime steps; merged the 'Why no customer request fails' table into a single failure table.
- Cut the detailed rationale on readiness ordering, residual-risk prose, the 'checks cover each other' paragraph (folded into one clause per check), and repeated restatements of the zero-failure argument.
- Simplified the 401 handling in per-request key use into three numbered cases, folding the 30-second rate limit into case 2.
- Folded the old CI-guard and redaction details into the single code-change PR step and shortened the staging drill and rollback text.
- Kept all fixed requirements and decisions unchanged (retries, 5-minute refresh, gate before revocation, rollback block, no cadence chosen); no plan behavior was changed.

### Holes
- Q1: What is the "managed secret store" here (which product), and how does a pod prove it is `orders-api-prod` when it calls it? What exactly does the platform hand the pod? (author: The brief says only 'our managed secret store' and does not name the product or the identity mechanism. The plan assumes the platform hands the pod an identity with no static credential (for example workload identity), but which product and mechanism is not known. Added to the assumptions, and step 1 now records both and step 2's probe verifies them.)
- Q6: When a 401 triggers a forced re-read and the version is unchanged, what does the caller of `charge` see? Is the order marked failed, and who retries it? (author: The charge call returns the provider error to its caller and logs a warning. The given files do not show whether the order is then marked failed or who retries it; that is existing order code which this plan does not change. Added as an open question for the orders-api team.)
- Q10: Step 8 check 3 says the old key's last-used time must be older than a refresh interval plus a margin. Where do I read last-used from, and how fresh is that data at each provider? (author: Not known where each provider shows last-used or how stale it is; the brief does not say. Step 1 now records both per provider, and step 8 check 3 requires the margin to exceed that recorded lag. Added as an open question for the security on-call.)
