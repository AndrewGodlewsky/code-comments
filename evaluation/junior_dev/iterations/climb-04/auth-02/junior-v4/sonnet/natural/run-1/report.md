## Review of auth-02 (junior-v4, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a short 'What this is' section and a Terms section (store, workload identity, snapshot, old and new keys) so a newcomer has context first (Q1).
- Step 12: added how the pod authenticates to the store with its workload identity token (Q1).
- Step 6: said what the old pods and old image contain versus the new image, and that no pod switches keys while running, so the refresh is not needed for this migration (Q2, Q3).
- Step 5: noted that running old pods are unaffected and are replaced in step 6 (Q3).
- Removed the internal version endpoint from step 7. Version ids now come from logs and the step 16 metric, checked per pod in the metrics service (Q4).
- Step 16: states per-secret version id and age metrics, and that step 7 uses them (Q4).
- Step 15: defined the new snapshot as a copy with only successful reads replaced, and what an in-flight request sees (Q5).
- Step 9: assigned image removal to the platform owner (registry and deploy pipeline list) and added a matching open question for the exact commands (Q6).
- Step 6 rollback now says it is a redeploy of the previous image via the normal pipeline (Q6).
- Step 4 and step 6: fixed the order. Staging gets the PR build before merge. Merge to main happens only after step 5, and the merge starts the prod rollout. This removes a risk that the merge rolled out an image before the prod keys existed (Q7).
- Step 10: made clear it is part of the step 3 PR and required before the step 6 merge (Q7).
- Added Assumption D (sandbox keys exist), step 1 now has the on-call write staging and dev sandbox keys, and added open questions for staging image source and missing sandbox keys (Q8).
- Trimmed wording in steps 1 to 3, 7 and 8 to offset the added text.
- Terms: workload identity now says the platform renews the token and the store client uses the current one on each read (Q9).
- Step 15: refresh uses the current token; a rejected token counts as a failed read, with a fresh token next cycle (Q9).
- Step 6: changed '3 or 4 old pods' to 4, noted a surge pod is possible but not relied on (Q10).
- Step 6: named who runs the canary and defined a healthy canary (error rate no higher than old pods, no key-rejected logs) (Q13).
- Step 1: added a read-only policy for the staging identity on orders-api/staging/* (Q11).
- Steps 11 and 12: APP_ENV is set by each cluster's deploy config and sets the store path (Q11).
- Step 14: stated that on a provider rejection the app only logs and waits for the next refresh (Q12).
- Step 8: explained that remaining traffic must come from non-pod callers and how to find them (Q14).
- Step 9: added the recovery sequence and the up-to-5-minute failure window for a pod holding a revoked key (Q15).
- Open questions: added dashboards (Q13) and what provider usage data shows (Q14).
- Reordered into the newcomer layout: summary, terms, assumptions, runtime, rollout, open questions last; runtime now comes first so rollout steps can rely on it
- Renumbered each part from 1 and replaced step-number cross-references to the other part with plain names, removing the 1-17 numbering
- Merged old steps 1 and 2 (prepare store, test policies) into one step
- Merged old steps 3 and 4 (build PR, stage test) into one step and folded the CI guard (old step 10) into it, with the required-check timing moved to step 3 of the rollout
- Merged rotation (old step 17) into a short 'Later rotations' note; moved local dev (old step 11) into the runtime part as a short section
- Cut duplicate rationale: repeated statements that the 5-minute refresh is not needed for this migration, the repeated rotation-cadence sentence, the optional extra-pod note, 'Starts it' verbosity and the long Old/New key explanation
- Merged the three old 'wrong value / fix' failure paragraphs into one-line handling and dropped the separate Scope section by folding the secret names into Terms
- Trimmed open questions to remove cross-step references; content of each open question kept

### Holes
- Q6: Step 9 says a pre-migration image holds a revoked key. In step 6 you can roll back safely. What exactly is the rollback mechanism (which tool/command) and where do you remove images from the deploy tooling? (author: Per deploy.md, rollback is redeploying an earlier image, so the mechanism is the normal deploy pipeline. I do not know which registry or deploy tool is used, so I do not know the exact commands for deleting images or removing them from the deploy tooling. The plan assigns this to the platform owner and lists it under Open questions.)
- Q8: What happens to the secrets for staging and dev: who writes them and what does 'non-production provider keys' mean for those same three providers? (author: Decided who writes: the security on-call writes the sandbox keys into staging and dev in step 1, and engineers can read dev. Whether all three providers offer sandbox or test keys is not known. It is now Assumption D, checked in step 1, with an open question for what to do if one has none. 'Non-production provider keys' now means those sandbox or test keys.)
- Q13: In step 6, how does the person watching the canary know the 'provider auth errors' or 'normal error rates' are there? Which dashboards or alerts do they use, and who is that person? (author: Who: the engineer on the deploy rota runs the rollout, with the security on-call reachable (now in step 6). Healthy means the canary's error rate is no higher than the old pods' and there are no provider-rejected-key log lines (now in step 6). I do not know which dashboards exist for error rate and provider auth failures, so this is listed under Open questions.)
- Q14: Step 8 requires no traffic for 30 minutes on the old key, but old pods are gone after step 7. If something does still use the old key (e.g. a developer's `make run`), how is that caller found from the provider's data? (author: By step 8 all orders-api pods are on new keys, so remaining traffic is from non-pod callers such as an old-checkout make run or scripts. How to find them depends on what the provider's usage data shows (time only, or source address and user agent), which is not known. Step 8 now says to use whatever the provider shows and ask likely teams, and the gap is in Open questions.)
