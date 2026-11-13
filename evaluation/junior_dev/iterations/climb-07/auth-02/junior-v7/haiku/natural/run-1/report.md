## Review of auth-02 (junior-v7, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Step 2 Moves: added that later rotations repeat this step as a new write to the same path, which answers who creates a new version (Q3).
- Step 4 Moves: added that old pods keep the keys baked into config/app.yaml, and wrote the one-pod-at-a-time sequence (new pod passes readiness, then one old pod stops) (Q2, Q5, Q8).
- A1 Reads: defined "latest version" as the newest version id the store holds for that name (Q3).
- A2 Moves: stated that a client call after the swap uses the new key and an in-flight request keeps the key it read (Q4).
- A2 Optional 401 line: named the provider client as the detector and the rate-limited extra re-read as the action, and noted the brief does not require it (Q7).
- A2 State: added the version-change log line as a fallback to the metric for Step 5 (Q6).
- Step 5 Checks: referenced the metric or the log lines as the way to read each pod's version (Q6).
- Step 8 rollback: made the pointer rollback conditional on the store supporting it, referring to Open question 7 (Q3).
- Section 0 Open questions: added 6 (secret store product and workload identity, Q1), 7 (moving back to an earlier version, Q3) and 8 (where the secret_version metric is viewed, Q6).
- A1: the HTTP server now starts listening before the gate, so /healthz can return 503 during retries. The earlier text said the gate ran before the server listened, which made the 503 rule impossible.
- A1: defined the attempt: one attempt fetches all three secrets, a failed attempt keeps nothing, and the retry repeats the full fetch (Q9).
- A1: removed the unexplained phrase 'liveness stays separate' and stated that no liveness probe is added, so a 503 does not kill a pod (Q11).
- A1 On failure: named the restart mechanism (container restart, crash-loop backoff) and pointed the unknown owner of a stalled rollout to Open question 10 (Q10).
- A2: named the failure counter secret_refresh_failures_total{name} and the new last-success timestamp gauge, so staleness has a metric; threshold and recipient left open as Open question 10 (Q12).
- A3: stated that each HTTP call, including each retry, reads the snapshot when it is made, and that one request uses one snapshot (Q13).
- Step 2: noted that the write route is not named and that the dev key owner is open, with a reference to Open question 6 and new Open question 9 (Q14).
- Step 3: added the open question about how an image reaches dev, and one line on how each of the three failure cases is produced in dev (Q15).
- Step 4 On failure: removed the sentence that said the pipeline blocks pre-migration images from that point on, which contradicted Step 8's start; the open owner of a halted rollout points to Open question 10.
- Step 6: Starts now also requires Step 8 to be in place, matching the rule that the marker must exist before old keys are disabled (Q16).
- Step 8: replaced the vague 'pipeline rejects images built before the migration' with a CI-stamped migration marker that the pipeline checks; the marker starts with the Step 3 PR; who configures the check is Open question 11 (Q16). Step 8 Starts now says it must be in place before Step 6, not only that it starts when Step 4 completes.
- Section 0: added Open questions 9 (dev keys and dev deploys), 10 (stalled rollouts and staleness alert) and 11 (image marker check owner). Open question 6 now also names the write route.
- Not changed: Step 4's use of 'start one new pod' under maxUnavailable 0 with no maxSurge, which deploy.md does not cover (see the earlier Q5 answer). Left for a later round.
- Added a three-sentence summary at the top, and a short 'How it works today' paragraph before Part A, so a newcomer knows the current system.
- Added a Terms section defining every name a newcomer would not know: provider, secret store, secret path, version id, KMS key, service identity, pod, readiness, liveness probe, rolling deploy with maxUnavailable 0, startup gate, SecretCache, sandbox key, soak period, migration marker, core dump and jitter.
- Moved the assumptions into their own short list after the terms, with the note that each is checked in Step 0 or listed as open.
- Merged repeated rules: the 'never log values' rule is stated once in the Part A rules and A4, not in each part; the 'Step 5 must be complete before revoking' rule stays only in Step 6.
- Split the start of Step 4 and Step 8 from the 'must be in place before' point, so each step has one clear trigger.
- Replaced cross-references such as 'Open question 6' and 'Q7' with plain statements of what is open, which point to the Open questions section by name.
- Kept every requirement, number, path, policy, metric name, timing and failure rule from the first version, including the Step 3 failure-injection methods, the Step 5 wait and inventory, the Step 9 log search, and the residual risks.
- Kept all eleven open questions, with the wording condensed but every point, dependency and suggested value kept.
- Added one sentence to Step 5 linking the old-key use check to the per-key last-used time that Step 0 confirms, from the first version's own Step 0 and Step 5 text.
- The 'What happens when things fail' section is a single paragraph that points to the runtime failure cases already written in A1 to A3, so failure handling is not repeated in a table.
- Corrected one typo in the A2 failure step (a metric name) so the text matches the metric in the rest of the plan: `secret_refresh_failures_top` is now `secret_refresh_failures_total`.
- A2: fixed the metric name to secret_refresh_failures_total{name}, matching the Q12 answer (Q17).
- A2: the optional 401 re-read now names its metric, provider_auth_failures_total{name} (Q18).
- Step 3: the 401 check is made only if the optional 401 re-read is built (Q18).
- A5: the guard reads the identity name from the store login and fails closed when it cannot; the source stays open (Q19).
- Step 4: added a write freeze from the start of Step 4 until Step 5 is confirmed; Step 2 says later rotations follow it (Q20).
- Step 5: the window starts when the last old pod stops; zero use is expected, with the traffic that could still appear and what to do if the last-used time is not zero (Q21).
- Step 8: stated that Step 6 cannot start if the pipeline cannot check tags.
- Rewrite: the summary is now short and states today's system in one paragraph; the failure table is the single place for runtime failures; the repeated log and secret rules are stated once in Part A; the open questions are referenced by topic, not by number, in the steps; terms and assumptions are unchanged apart from wording; no stated brief requirement was cut.

### Holes
- Q1: What exactly is the "secret store" here (which product), and how does a pod prove it is `orders-api-prod` when it calls it? (author: The brief names "our managed secret store" with per-environment KMS keys, but not the product, and not how a pod proves it is orders-api-prod. Added as Open question 6. Not invented here.)
- Q3: What does "latest version" mean for a secret, and who creates a new version when Security rotates a key? Is the "current pointer" the same as the latest version? (author: "Latest version" means the newest version id the store holds for that name. The brief says every write gets a new version id. Rotation is a new write to the same path by Security on-call (Step 2 now says so). The brief does not say the store has a separate current pointer that can move back to an older version. Step 8 assumed one, so it is now conditional and listed as Open question 7.)
- Q6: How does Step 5 get each pod's version id? Who looks at the `secret_version` metric, and where is it viewed? (author: A2 defines the secret_version metric, but the brief names no metrics backend or dashboard, so where it is viewed is unknown. Added as Open question 8. The version-change log line is a fallback in the central logs (30-day retention) and is now named in A2 and Step 5.)
- Q10: What starts a new attempt after the pod exits non-zero, and who notices that a deploy is stalled and acts on it? (author: The restart is decided: a non-zero exit makes Kubernetes restart the container, which runs the gate again from the start, with the usual crash-loop backoff. Nothing in deploy.md or the brief names who notices a stalled deploy or acts on it. The rollout halts (deploy.md), but the owner is not known. Added as Open question 10.)
- Q12: Who gets the staleness alert, what is the threshold for it, and which metric is it computed from? The text says the metric is incremented on failure but alerts on time since last success. (author: The metric is decided: failures increment secret_refresh_failures_total{name}, and each successful read sets secret_last_success_timestamp{name}, so staleness is now minus that timestamp. The threshold for a staleness alert and the person or team who receives it are not in the brief or the files. Added as Open question 10.)
- Q14: How does Security on-call write to the store, and does the dev write go through the same route? Who creates the dev sandbox keys? (author: The brief does not name the store's write route, so how Security on-call writes values is not known (Open question 6). It also does not say who creates the dev sandbox keys or who writes them to orders-api/dev/*. Step 2 now says both are open, and they are listed as Open question 9.)
- Q15: How does the image get deployed to dev, automatically or by hand? How are the failure cases (store unreachable, mid-run failure, revoked key) produced in dev? (author: The files do not say whether an image reaches dev by hand or automatically; deploy.md covers only prod. The plan now says this is open (Open question 9). The failure cases can be produced in dev as follows: an unreachable store by blocking the pod's route before start, a mid-run failure by removing the dev read permission for one refresh window, and a revoked key by disabling the dev sandbox key at its provider. These are design choices, and Step 3 now lists them.)
- Q19: How does startup learn which identity it is running as, so it can refuse `orders-api-prod` when `APP_ENV` is `dev`? Does the store tell it, or is the identity configured somewhere? (author: The brief does not say whether the store reports the caller's identity or whether the identity is set in config. This is open (Open questions). A5 now says the guard reads the identity name from the store login and fails closed: if the name cannot be read, startup refuses to run.)
