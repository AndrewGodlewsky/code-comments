## Review of infra-01 (junior, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Rewrote the 12-item checklist as numbered steps in deploy order, each with its trigger, what it changes, where its state is kept and what happens on failure.
- Added a terms section for colour, target group, public and test listeners, deploy lock and switch time.
- Decided the deploy lock is CI's single-run concurrency group, held from merge to end of the rollback window.
- Decided the live colour is read from the public listener, and recorded release and state as target-group tags.
- Added the test listener as a second CI-only listener on the idle colour, and the abort, rollback and teardown rules that the brief left open.
- Kept every fixed requirement from the brief, including the additive-only migrations and the 10-minute abort rule.
- Added an open-questions section for the dead-run watch gap, the 5xx metric source and the smoke suite contents.
- Rewrote the whole document for a newcomer: a three-sentence summary, a terms list, then numbered steps, the state section and open questions, in the order the skill asks for.
- Each step now has Starts, Does, Keeps and If it fails lines, so the failure handling sits with the step it belongs to, not in a separate table.
- Defined the test listener in the terms and added its rule repoint to the idle group at step 6, because the smoke tests need a route to the new instances (Q17).
- Step 2 now covers rollback-window colours (wait or shut down), and any other non-live colour that still has running instances, so a failed shutdown from step 9 or step 12 is cleared by the next deploy (Q10, Q11, Q15).
- Step 2 now states the cases in which a rollback-window colour exists (Q10).
- Step 9 states that the idle colour's state tag is unchanged on abort, and that a failed shutdown is cleared by the next deploy (Q12).
- Step 10 separates the listener change from the tag writes, retries a failed tag write, and stops the run without moving the listener back (Q13).
- Step 11 adds a check of the listener before each reading, so a manual rollback stops the watch, and states that only windows inside the 15 minutes count. An unreadable count stops the run and leaves the old colour up (Q16).
- Step 12 fixes the order of its actions (repoint, tag, shut down) and states each failure path, including a shutdown that fails after the repoint (Q15).
- Step 13 states that it does not take the lock, and how the run notices a manual rollback (Q16).
- Step 14 checks the listener before shutting down the old colour, so a rollback that already happened is not undone, and tags retired only after a successful shutdown (Q14, Q16).
- Step 15 applies to every run, including every early stop, so the lock is never left held.
- Added a Where deploy state is kept section, listing the lock, the listener, the test listener rule, the tags and the migration history table.
- Open questions: added the failed-tag hole, the race between a manual rollback and the step 14 shutdown, and who sets up the test listener. The original three questions are kept, reworded.
- Summary now says how the system works today (a merge restarts catalog-web in place) and gives the main flow in three sentences.
- Terms: the release tag now has a definition with its purpose, so a reader knows why it is kept.
- Step 1: says the lock can be held up to 30 minutes after the switch, so a queued merge waits that long.
- Step 2: says its wait comes before step 6, so the 10-minute deadline has not started, and that the wait is at most 30 minutes.
- Step 9: says migrations stay applied after an abort.
- Step 13: says the procedure does not tell the engineer when a rollback is advisable.
- Step 14: says the run waits, holding the lock, from the end of the watch until 30 minutes after the switch.
- Tag rules are in one section under Where deploy state is kept; the steps no longer repeat them.
- Test listener setup moved to its own section, Setup before the first deploy, separate from how the deploy runs.
- Open questions: added the question of which tool CI uses to shut down and tag, and what counts as shutdown finished, and the missing alert between minute 15 and minute 30.
- Summary: cut to three sentences. It now says how the system works today (in-place restarts) and why the flow is shaped as it is: a rollback is one change because the old colour stays up.
- Terms: added one-line definitions for load balancer, concurrent index and rollback, which the steps use. Each term is defined once. Kept the existing definitions of the rest.
- Steps: kept every step, number, limit and rule from the first version, including the 10-minute deadline, the 10-second checks with 3 passes, the 1% over any 5-minute window, the 15-minute watch and the 30-minute window. Each step keeps its Starts / Does / Keeps / If-it-fails layout.
- Steps: put the reasons from the answers in the step they belong to, in one clause each: why the lock is held (step 1), why step 2 waits (before the rollback decision in step 13), why the listener is not moved back after a tag failure (step 10), why step 12 repoints before tagging (step 12), and why step 13 does not take the lock (step 13).
- Step 2: the wait rule is stated once, with its cap and its reason. The 'why this case exists' note now follows the rule it explains.
- Step 13: said once that the procedure gives no advice on when to roll back, and pointed to the open questions. The repeated wording was removed.
- Step 14 and step 12: removed repeated wording about the tags and the state. Each rule is now stated in one place.
- State section: added that an idle colour is never tagged live or rollback-window (from the answer to Q12), and that no step reads the release tag, with the reason (from Q20).
- Setup: moved the test listener setup into its own section on rollout, separate from how each run works, and noted that it runs once.
- Open questions: kept all eight from the first version. Did not add new ones. The spike-window wording still says 'lies within the 15 minutes', as the first version did. Answer Q8 said 'ends within', which is a different rule (see the holes below).
- Removed the codes and cross-references that did not add meaning. Kept 'step N' references only where the flow goes to another step.
- Length: about the same as the first version. The steps are longer, because the reasons are added inline, but the summary and the state section are shorter.

### Holes
- Q6: What is the test listener, and what do the smoke tests cover? What happens if they fail? (author: The test listener is my design, and it is marked decided above: a second listener on the same load balancer, reachable only from CI, that forwards only to the idle colour. I did not check what the smoke suite covers, and the brief does not say. If the smoke tests fail or do not finish within the 10-minute deadline, the deploy aborts with the public listener untouched.)
- Q19: How does the deploy run "shut down" instances and "tag" a target group in practice? Which tool or API does CI call, and what does it consider shutdown finished? (author: The brief does not name a tool or API for shutting down instances or tagging a target group, and the document does not choose one. What counts as shutdown finished (instances gone, or deregistered from the target group) is not defined here. This is listed under Open questions.)
