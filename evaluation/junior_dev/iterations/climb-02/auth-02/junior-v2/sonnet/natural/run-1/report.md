## Review of auth-02 (junior-v2, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Approach: stated that old and new keys are used side by side by old and new pods (Q1).
- Step 2: also record whether each provider shows a key's last-used time (Q6).
- Step 3: named the security on-call group and said the recorded version ids are the expected ids for step 8, updated if a key is rewritten (Q6, Q8).
- Step 4: fixed a wrong cross-reference, the code merges in step 7 not step 6.
- Step 7: record the image digest; made the hold after the first pod a manual pause decided by the person running the deploy (Q4, Q8).
- Step 8: check against the recorded digest and recorded version ids instead of vague 'post-migration image' and 'expected version id' (Q8).
- Step 10: said where last-used comes from and added a fallback when a provider shows none (Q6).
- Step 12: explained pod identity in plain terms and that readiness makes no provider call (Q2, Q5).
- Step 14: clarified what 'previous' is, when it is replaced, and that it is used only in step 15; defined the secret_refresh_ok log line and how the alert works (Q3, Q7).
- Assumptions: added provider last-used support, pod-to-store auth mechanism, and log-service alert support.
- Approach: added that old pods never read the store and are unchanged until step 10 (Q9).
- Step 5: secrets module holds keys in memory, clients read memory on every call, only startup load and refresh call the store (Q10).
- Step 13: added that memory is written only by steps 12 and 14 (Q10).
- Step 12: stated that the app always reads the latest version and never pins one (Q11).
- Step 7: replaced the vague error-rate check with a concrete continue rule (smoke calls succeed, no 401/403 in logs), and moved it out of the failure list into its own item (Q12).
- Step 8: simplified the check to the latest log line per secret matching the recorded version id, and dropped the 'no older line afterwards' clause (Q13).
- Step 15: said the client cannot tell the cause of a 401/403, what the customer waits for, and that the original failure is returned if the retry fails (Q14).
- Step 9: corrected the reason for blocking old images to rollback onto revoked keys (Q15).
- Assumptions: added that the tooling can enforce do-not-deploy on image tags (Q15).
- Merged the 'Open question' and 'Assumptions to confirm' sections into one 'Open questions' section at the end.
- Cut the removed-by-repetition detail in step 3 failure handling (three bullets merged into one line).
- Merged step 6's two failure bullets into one and moved the negative test into the PR; dropped the throwaway-PR check.
- Shortened step 11 to a single what-moves line and folded the do-not-deploy verification into it.
- Merged step 15's separate safety and 'why safe' notes into the numbered fallback list; condensed step 13 and step 14 wording.
- Folded step 1's 'step is done only when' and several access sub-bullets into tighter lists; removed duplicated explanations in the approach section.
- Trimmed step 2 inventory list into one sentence and merged its two checks.
- Kept step numbering so cross-references stay valid; no mechanisms were added or removed.

### Holes
- Q2: What is the 'managed secret store' here, and how does a pod prove who it is to it? What does 'the pod's identity (orders-api-prod)' mean in practice? (author: The brief only says 'our managed secret store' and gives no product or auth mechanism. The pod's identity is the cluster service identity orders-api-prod from deploy.md, which the platform attaches to the pod, so no credential sits in the image or env. The exact proof mechanism (for example workload identity) is not known; I added it to Assumptions.)
- Q6: Who is 'the security on-call' and how do they find the provider's 'last used' time for the old key in step 10? Is that something every provider shows? (author: The security on-call is the group given write on prod secrets in step 1. Where each provider exposes 'last used' (dashboard or API) is not known, and not every provider may show it. I added that to step 2 as something to confirm, to the step 10 gate, and to Assumptions, with a fallback of disable-first and a day of watching errors.)
- Q12: In step 7, how is it decided that the first new pod is bad and the rollout must be stopped or rolled back? What does the deploy person look at to judge the 'error rate'? (author: The plan now gives a concrete rule: continue only if the per-provider read-only calls succeed and the new pod's logs show no 401 or 403. Which dashboard or metric the team uses for a broader provider error rate is not known, so I dropped the vague 'error rate' wording. The smoke calls are in Assumptions.)
- Q15: Step 9 says old image tags contain the leaked keys. Why is that an issue if the keys are revoked in step 10, and who enforces 'do-not-deploy' in the deploy tooling? (author: The real problem is rollback: after step 10 an old image would run with revoked keys and fail every provider call. The leaked keys are dead by then, so that reason is secondary. Which tool enforces do-not-deploy (registry delete or deploy tooling policy) is not known; it is now in Assumptions.)
