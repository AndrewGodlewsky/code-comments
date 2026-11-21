## Review of auth-02 (junior-v5, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Replaced the 'Scope and fixed points' section with a plain summary paragraph, a terms list and a roles list, so a newcomer has the terms before the steps (Q1, Q6).
- Step 4: defined what 'Part B ready for release' means (approved in the change ticket, not merged or deployed) and why that order matters (Q4).
- Step 5: named security on-call as the launcher and reader of the check job output, and linked the identity mechanism to Open questions (Q1, Q7).
- Step 6: stated that the old keys remain in git history and that the interim exposure window runs until Step 10, and added it to Open questions (Q3).
- Step 8: explained that old pods read their image's config file and never read the store, so the image decides the key in use (Q2).
- Step 10: defined how a pre-migration image is identified (a build-commit label, allowed only from the Step 6 merge or later) and listed the mechanism and owner as open (Q6).
- Part B Step 14: made explicit that the client reads SecretStore memory and makes no network call (Q5).
- Rollback section: replaced the single table with one that states the overlap is intentional, plus the rule after Step 10 (Q8).
- Merged the duplicated 'what happens when things fail' notes into one failure table, and removed references such as 'open question 1' in favour of named questions.
- Open questions: added the store product and identity mechanism, the interim exposure window, the deny-policy mechanism and owner, the Part B sign-off owner and the Step 5 launcher, and the liveness probe check. The retry, soak, usage, cadence and image-deletion questions are kept.
- Shortened long sentences throughout and kept the Part A (rollout) and Part B (runtime) sections separate. The file is still within about 1.5 times its first length.
- Reordered the sections so the runtime behaviour (Part 1) comes first, because the rollout deploys that code. Kept the rollout as Part 2. Each section now has its own heading.
- Added a short summary that says how the system works today and how the main flow goes from start to finish, and why the rollout waits for revocation.
- Added one-line definitions for every term a newcomer needs: secret path, KMS key, version id, service identity, overlap, revocation, pre-migration and post-migration image, SecretStore, readiness, liveness, config guard, deny policy.
- Merged the Roles section into the terms, as a short list of who does what.
- Replaced cross-references such as 'Step 12' and 'Part B, Step 16' with the step's own name, so each step reads on its own.
- Added the answer to Q2 to rollout step 8: the image, not the store, decides which key a pod uses.
- Added the answer to Q5 to runtime step 3: clients read SecretStore memory and make no network call.
- Added the answer to Q3 to rollout step 6: the api_key lines are removed, the old values stay in history, and the interim exposure is stated in the step.
- Added the answer to Q4 to rollout step 4: 'approved' means reviewed and ready to merge, recorded by the change owner, and the order of the parts is explained.
- Added the answer to Q6 to rollout step 10: each image carries its build commit as a label, and the policy allows only the merge commit or a later commit on main. Its owner is left open.
- Added the answer to Q7 to rollout step 5: security on-call starts the check job and reads its output, and the identity mechanism stays an open question.
- Added the answer to Q8: the rollback table now has a rule paragraph and explains why the rows overlap.
- Merged duplicate rules into one place: the 'missing metric is not a pass' rule appears once in rollout step 9, and the 'do not revoke while the fleet is mixed' rule appears once in rollout step 8.
- Added a fact-check of the start-up and refresh timings (retry, jitter, staleness) as plain sentences in the runtime steps, with the retry count kept as an assumption.
- Merged the store-features and per-key-usage open questions into one item, and merged the two sign-off questions into one item. Kept all other open questions from the original, unchanged in substance. Did not choose a rotation cadence.
- Kept the failure table with one row per failure, using the new step names, and added a plain 'Where' column.

### Holes
- Q1: What is the "managed secret store" here (which product), and how does a pod authenticate as `orders-api-prod` without credentials in environment variables or on disk? (author: The brief does not name the managed secret store product, and it does not say how a pod proves the orders-api-prod identity. deploy.md confirms that pods run under orders-api-prod. The plan assumes the platform attaches the identity to the pod, so no credential is in env vars or on disk. This is added to Open questions.)
- Q6: How does the deploy policy in Step 10 identify an image as "built before Step 6", and who or what applies it? (author: The plan did not define how the deny policy identifies a pre-migration image. Step 10 now uses a rule: each image carries its build commit as a label, and the policy allows only images from the Step 6 merge or a later commit on main. How the registry reads that label, and who owns the policy, are not known and are added to Open questions.)
