## Review of auth-02 (junior-v4, author sonnet, seeded-implicit)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote the plan into a short summary, terms, runtime section, rollout steps and failure table, because the questions showed a newcomer could not follow the original terse list.
- Separated runtime behavior (startup, ready, use, refresh) from rollout steps, so Q3, Q4 and Q5 are answered in the file.
- Made clients call secrets.get() on every request rather than copying the key in __init__. This fixes a real hole: copying at construction would stop a rotated key from reaching running pods.
- Made /healthz return 503 until keys load, and defined secret_versions as version ids only. Readiness now gates on the keys, as the brief requires.
- Defined APP_ENV as the path selector, and made the app exit if it is unset, so it never defaults to prod.
- Spelled out the rotation sequence: new provider key, new store version, wait for every pod to show the new version, then revoke. This meets the no-failure requirement.
- Added rollback notes that account for revoked yaml keys.
- Added open questions for the store product and authentication, and for whether providers allow two live keys. The rotation cadence stays open.
- Added the access policy details, the CI check behavior and the retry count. The file is longer than 1.5x because the brief's required content was missing.
- Merged the summary into a two-sentence opening that says how the system works today and how the main flow goes
- Moved the 'keys live only in memory' rule from step 1 to a single line above the runtime steps, so it is said once
- Split rotation step 5 into a numbered sub-list (a to d became 1 to 4) and gave it a State line
- Gave the Deploy step and rollback-notes step the same parts as other steps (starts, state, failure), and made the rollback-notes step name its trigger
- Replaced the reference 'step 5(d)' with 'step 5.4'
- Trimmed repeated wording in the Deploy, Ready and Use steps

### Holes
- Q1: What is "the store"? Which product is it, and how does the app authenticate to it? (author: The brief only says 'our managed secret store'; the product and how a pod authenticates as orders-api-prod are not given. Added to Open questions rather than guessing.)
