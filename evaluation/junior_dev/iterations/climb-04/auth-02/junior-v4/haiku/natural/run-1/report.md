## Review of auth-02 (junior-v4, author haiku, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Rewrote the opening as a summary plus a short list of terms, so a newcomer sees the main flow first.
- Removed Step 11 (temporary compatibility code). Nothing adds such code, and the issue closure moved into Step 10.
- Corrected Step 5: only v2 pods read the store and refresh; v1 pods keep key A from their image.
- Step 7: states that each new pod reads keys, binds the port, and passes readiness, and what the rollout waits on.
- B2 step 4: added logging of each loaded version id, needed by the Step 8 check.
- B3 and B4: stated that in-flight calls keep their value and that refresh failures keep the last good value.
- B5: explained why a pod without keys is never ready.
- B9: stated the dev and prod selection through APP_ENV.
- Added a failure summary table, including the revoked-key-before-refresh risk.
- Replaced internal codes (A2, A3, G1, B1 to B10 cross-references) with plain names, so the file does not send the reader elsewhere.
- Moved the retry count and secret names to open questions rather than assumptions. Left out exact formats and library choices.
- Kept the brief's fixed requirements: store paths, access policy, retry at startup, 5-minute refresh, memory-only values, no key revocation before all instances use the new key, CI guard, local dev without prod reads, and the open rotation cadence.
- Replaced internal codes (B1 to B10, Part A/B references) with plain section names, so no step sends the reader elsewhere to look up a code.
- Moved the 'how it works today' explanation into the Summary, in two sentences, as the skill's layout requires.
- Merged the Step 3 offline mode text and the Local development section into one place in Step 3, removing the repeated statements that prod is unreachable locally.
- Merged the Readiness section (B5) into the Startup and Readiness sections and the failure table, so the 'port is not bound until keys load' rule is stated once in Startup.
- Merged the Memory handling section (B7) into one Memory rules list, and removed the repeated 'values stay in memory' statements from Steps 3, 5 and 7 and from Refresh.
- Removed the duplicate 'open option' wording from Provider errors. The item now lives only in Open questions (item 6).
- Restated the runtime sections (Startup, Clients, Refresh, Provider errors) with the same parts as the rollout steps: starts, does, keeps data, on failure.
- Clarified the CI guard timing: it is added on the Step 4 branch and goes live with the Step 6 merge. The old text said both 'add in Step 4' and 'turned on in Step 6', which read as a conflict.
- Kept the startup guard (non-zero exit on any api_key in yaml) with the config section, and kept the CI guard as its own section, since they are separate checks.
- Shortened Open questions wording without changing what is asked. Item 4 now says 'retry count at startup', and item 9 keeps the no-interval rule.
- Kept the plan's intent: no new mechanisms were added, the retry count, secret names, rollout order, revocation rule and every fixed requirement are unchanged. No step was removed.

### Holes
- Q1: What exactly is the 'managed secret store' (which product), and what is 'workload identity'? How does a pod prove it is orders-api-prod to the store? (author: The brief names only 'our managed secret store' and does not name the product, nor the mechanism a pod uses to prove its identity. Workload identity is described in the file only as the identity the cluster gives the pod, which the store checks. Logged as open question 1. Changed: Terms section now defines both terms in plain words, and the file states that no static credentials are stored on disk.)
- Q2: Who or what actually triggers the rolling deploy and builds the image? Is 'operator starts the deploy' a manual command, and what tool does it use? (author: deploy.md says rollouts are rolling with maxUnavailable 0 and that CI builds the image, but it does not name the deploy tool or who starts a rollout. The plan says an operator starts it after Step 6 is approved. The tool is logged as open question 2.)
- Q5: What does the on-call do when writing B to the store: which tool or console, and how does a store write produce a version id that the refresher compares? (author: The tool or console the on-call uses to write B is not known. The mechanism the plan relies on is that the store returns a version id on each write, and the refresher compares the id it last loaded with the id the store returns. Logged as open question 3. Changed: Step 5 names the ticket record and the provider-console check; B4 states the comparison.)
- Q9: Step 3 says dev uses the engineer's identity via make run. How does a laptop get that identity, and how does the loader know it is in dev mode versus prod? (author: How a laptop gets the engineer's identity is not known, because the brief does not name the store's authentication method. The decided part is the mode selection: make run sets APP_ENV=dev, the loader reads prod only when APP_ENV=prod, and only pods set that (B9). Logged as open question 3.)
