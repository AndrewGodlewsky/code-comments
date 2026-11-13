## Review of auth-02 (junior-v3, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Summary: added the APP_ENV path rule so the environment name is explained up front (Q2).
- Assumptions, step 1 and Open questions: added the store product and pod-to-store identity as something to confirm, marked unknown (Q1).
- Step 5: version ids are recorded on the ticket (not just for step 13) so later corrected versions are tracked (Q6).
- Step 6: stated that a provider rejection returns the error to the caller with no new retry, and why that is safe (Q3).
- Step 7: spelled out that the path is built as orders-api/<APP_ENV>/<name> (Q2).
- Step 10: the version endpoint is per pod and cluster-internal only; dropped the metric alternative (Q5).
- Step 12: defined the gate as real traffic on the first new pod plus the on-call test call, and stated that old keys stay usable on purpose (Q4, Q8).
- Step 13: pod list and image check made concrete, pods queried one by one, comparison is against the latest validated version id in the store (Q5, Q6, Q8).
- Step 14: replaced the misleading 'keep the new key' with the real recovery of moving the missed consumer to the new key, and named the residual risk (Q7).
- Open questions: now a list, adding the store identity and the rollout pause mechanism.
- Reordered into the newcomer layout: summary, terms, numbered steps with failures per step, open questions at the end
- Merged the old Summary bullets (keys, rotation, overlap, app changes, environment name) into one short paragraph and moved the environment name and no-default rule into a Terms list
- Added a Terms section defining store, names, APP_ENV, security on-call, overlap and version endpoint
- Folded the assumptions list into one short section and moved the store-facts and identity items into it
- Collapsed 'State lives in' lines, keeping only the facts a reader needs (memory only, replaced as a whole, no disk) and dropping the repeated ones
- Merged the loader raising on api_key into step 6 and removed the separate Config file and Loader bullets from step 11
- Merged the Local dev fallback and no-default-env notes into Terms and step 3
- Cut the 'Why a pod can't be stuck on a bad value' heading into a plain 'if a bad version was written' line in step 9
- Removed the 'on-call's own test call from step 5' gate item in step 12 to keep the gate to one check
- Dropped the 'Why this order matters' heading by folding the reason into step 5
- Shortened step 10 and step 15 and removed references like 'see step 12', keeping only the essential step numbers that name the ordering constraints

### Holes
- Q1: Which product is the "managed secret store", and how does a running pod prove it is identity `orders-api-prod` when it reads from it? (author: The brief does not name the store product or the mechanism by which a pod proves it is orders-api-prod; it only fixes the identity and paths. I will not guess. Added to the assumptions, to the step 1 checks (Identity) and to the open questions.)
