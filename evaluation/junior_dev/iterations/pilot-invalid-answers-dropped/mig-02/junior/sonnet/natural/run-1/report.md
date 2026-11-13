## Review of mig-02 (junior, author sonnet, natural)

Rounds: 4. Ended: cap.

### What changed
- Removed the unused mode epoch from the rollout record (Q2).
- Added a 'Who runs it' section defining the rollout controller as a service, what it does and that it resumes from the rollout record (Q1).
- Replaced the undefined 'queued charges' with 'due and uncharged in the ledger', and changed steps 1, 5 and 6 and the diagram to match (Q3).
- Defined 'unknown outcome' as a ledger entry still 'attempting', added the write-ahead 'attempting' entry to the ledger description, and spelled out the provider-unreachable behaviour in step 2 and the diagram (Q4).
- Made Pin events and Reprocess apply only from new_only, moving the choice state before them, and explained why Verify still runs from shadow or both and how the ledger shows what the new engine charged (Q5).
- Clarified that the old engine reads no events in new_only, that reprocessing skips ledger-charged periods and charges nothing, and changed the ReprocessSkipped to VerifyNoGaps label accordingly (Q6).
- Fixed the Decommissioned transition: a person retires the old engine on or after day 35 and never during a rollback; added the rule for a rollback running at day 35 (Q7).
- Stated that the ledger and provider idempotency keys, not flag freshness, prevent double charges, and added open questions 6 to 9 for the record location, worker read mode and staleness, provider-unknown time limit, and old engine catch-up (Q8).
- Added the Finance sign-off to the Gate B line and a 'controller crashes mid-rollback' failure case.
- Defined the auto-trigger as a charge-failure monitor that reads ledger results and sends the controller a rollback request; added open question 12 for where it runs (Q10).
- Stated that the controller runs all steps and that day 35 is counted from entry into new_only per the rollout record, and why it matters for event expiry (Q14).
- Step 1 now waits one staleness bound after setting the fence before step 2, and open question 7 says a maximum must be set (Q11).
- Added a diagram edge from VerifyNoGaps back to SettleInFlight and failure-table row for stale workers' late attempting entries (Q11).
- Step 4 now says the old engine writes invoices to the shadow store, not the ledger, and what its own state is; open question 9 expanded (Q9).
- Step 5 defines due periods and lists concrete gap types and fixes; added open question 10 (Q13).
- Step 6 now sets the flag first, then clears the fence, explains the window and crash behavior; diagram label updated (Q12).
- Defined the mismatch rate formula and per-night reading of gate A; added open question 11 on unresolved mismatches; extended assumption 2 (Q15).
- Clarified that the fence applies to both engines and that the ledger key is the real double-charge guard; shadow store now described as holding uncharged invoices.
- Diagram: added a start choice so rollback from shadow goes straight to FlipFlag with no fence, because the old engine keeps charging (Q20).
- Diagram: VerifyNoGaps now returns to ReprocessSkipped when a due uncharged period has events past the checkpoint, replacing the unclear 'fix and re-check' loop (Q18).
- Diagram: the double-charge case now says on-call fixes it by hand and the check repeats.
- Step 4 rewritten: defines the old engine checkpoint, says the invoices are a dry run not used for charging, and says why the checkpoint must be current (Q16, Q17).
- Step 5 gap list rewritten around the checkpoint and the ledger states, and the 'invoice from the old engine' wording removed (Q18).
- Ledger bullet now defines attempting, charged and failed, and says only charged counts as a charge (Q19).
- Step 6 now says the old engine recomputes the invoice from events at charge time and retries failed periods (Q17, Q19).
- Shadow store bullet and mode table updated to match; the fence bullet says shadow rollbacks never set it (Q20).
- Intro to the rollback steps says shadow rollbacks skip steps 1 to 5 (Q20).
- Who runs it: added the nightly comparison job and how its results become gate counters and a status the person can see (Q21).
- Auto-trigger text now says retries count as attempts, an empty window means no trigger, and duplicate requests are ignored (Q22).
- Failure section: added the declined-charge case.
- Open questions: reworded 3 and 9, added 13 (job host and status display) and 14 (retry of declined charges).
- Added a 'A promotion has three steps' paragraph under Who runs it, answering what a promotion does beyond setting the flag (Q23).
- Added to step 4 the stated assumption that the checkpoint advances by reading events, flagged as unverified (Q24).
- Added a 'Paging on-call' paragraph listing which cases page and that the system stays in a safe state until a person acts; added on-call hand-resolution hints to steps 2 and 5 (Q25).
- Clarified in step 6 that the old engine picks periods from the ledger and billing schedule, not the checkpoint, and marked it unverified (Q26).
- Extended open question 9 to cover the checkpoint-advance and period-selection assumptions.
- Added open questions 16 (paging and on-call runbook) and 17 (how the old engine is shut down on retirement).

### Holes
- None.
