## Review of ml-01 (junior, author sonnet, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Step 1: added what the store holds (rows stamped with copy time), failure behaviour and the 6 hour rule.
- Step 2: added what a version stores, who assigns numbers and which steps change aliases.
- Step 3: added how features are fetched, the 30 ms limit, 150 ms budget, exact fallback triggers (including model error) and where popular items live.
- Step 4: added the 30 second poll, background load, the feature check and its failure handling.
- Step 5: added user selection by hash, queue message contents, worker behaviour, log row and drop-on-failure handling.
- Step 6: stated what the comparison job reads and outputs.
- Step 7: spelled out the promotion criteria from the brief instead of referring to them.
- Added an Open questions section for the A/B decision.
- Step 3: added the 80 ms model-call limit, the model-timeout fallback, and the exact response shape with the fallback flag (Q9, Q10).
- Step 4: added startup behavior (load before ready, stay not ready on first-load failure), and clarified the feature check compares feature names at load time only (Q11, Q12).
- Step 5: added how shadow workers load the shadow version, and what happens when the alias is unset or changes (Q13).
- Step 2: stated shadow-start is a manual command, not automatic (Q14).
- Steps 6-8: days in shadow counted per version; promote is a command run by the ML lead that checks criteria, records the approver and performs the switch (Q15).
- Open questions: added that who may run shadow-start, promote and rollback is undecided.
- Step 1: each materialization run also writes the feature-name list that the step 4 feature check reads (answers Q17).
- Step 3: model runs in-process on the user's feature row; instances keep the last popular list if the daily recompute fails (Q18, Q19).
- Step 4: instance loads the popular list before ready; loaded model held in memory and swapped in one step without dropping in-flight requests; failed rollback load keeps current model and alerts (Q16, Q19, Q20).
- Step 5: shadow queue message and prediction-log row now carry time, active version and active items, as well as shadow version and items (Q21, a real gap).
- Step 6: report is dated; overlap and days in shadow are computed from the new log columns (Q21).
- Step 7: promote also refuses unless the version is the current shadow alias and has a report from the last 24 hours (Q22).
- Open questions: added candidate pool, consecutive days, and log storage and popular-list publishing location.
- Replaced the two-line summary with a short summary that states how the system works today (nightly precompute) and the main flow.
- Added a Terms section defining online store, materialization, feature list, registry, alias, popular list, fallback, shadow, shadow queue, prediction log and feature check, each in one line.
- Merged scattered limits (150 ms, 30 ms, 80 ms, 6 hours, 1 minute, no redeploy, never run against missing features) into one 'Rules that apply throughout' section, and removed repeats from the steps.
- Split the old step 4 and the old promote and switch steps cleanly: model loading now carries the swap, background load, startup and failure behaviour; the old switch step is merged into promote because the command does the switch.
- Renumbered to 8 steps, and each step now states its trigger, data movement and failure handling, with the old step 8 (switch) folded into step 7.
- Added a failure table, and moved failure lines out of the steps where the table says the same thing.
- Kept the open questions, and noted that the 80 ms model limit and the 24 hour report limit are my choices.
- Cut the repeated explanation of the feature check from steps 3 and 5, and the repeated statement about the response never using shadow output.
- Added 'no cache' and 'fallback reads memory only' to step 3 from the answers.
- Did not add exact formats, library choices or rare edge cases; those stay in the answers.

### Holes
- Q18: What does the model call on an API instance actually do: is it run in-process in the instance, or a call to another service? What goes in and what are the 20 item IDs ranked from? (author: I decided the model runs in-process in the API instance (loaded from the registry), with the user's feature row as input; stated in step 3. I do not know what candidate pool the 20 items are ranked from or how the instance gets it. Added to Open questions rather than guessing.)
