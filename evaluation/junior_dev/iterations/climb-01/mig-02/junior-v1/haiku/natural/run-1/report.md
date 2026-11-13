## Review of mig-02 (junior-v1, author haiku, natural)

Rounds: 3. Ended: teachback-correct.

### What changed
- Added a 'Who does what' section that says what the controller does and what a person does, answering Q1.
- In shadow mode, stated where each engine's invoice is read from for the nightly comparison, answering Q3.
- In both mode, stated that customers receive the new engine's invoices and that the old engine's output is only compared, answering Q8.
- Rewrote RB1 to RB3 as numbered steps: how in-flight charges are resolved by idempotency key, what reconcile compares and when it fails, and how RB3 selects due uncharged invoices, answering Q5, Q6 and Q7.
- Added open questions for how engines learn billing_mode, what counts toward 5,000 invoices, how the failure rate is measured, how the RB1 freeze is switched off, and who is notified on rb_stalled, answering Q2, Q3, Q4, Q5 and Q6.
- Stated that the ledger is the system of record and the provider holds payment status, and that the shadow store is never customer-facing.
- Merged the duplicated rollback text in the failure section and kept the diagram unchanged.
- Diagram: the RB1 to RB2 label now states its trigger, every in-flight charge has a known provider status.
- Diagram: the both to new_only gate now says no open mismatch, instead of no unresolved mismatches, and the new_only to retired label now says after day 35 and that a person decides to decommission.
- Modes, both: added that the comparison continues with the sources swapped (ledger for the new engine, shadow store for the old), that the ledger is the reference, and that a mismatch goes to a person rather than being corrected automatically (Q9).
- RB1: added that RB1 waits until every in-flight charge has a known status, that an unknown charge is looked up again and never re-sent, and why (Q12).
- What happens when something fails, gate: added that the both to new_only gate needs no open mismatch at approval (Q10).
- Automatic rollback: added that who is told is open (Q14).
- Rollback stalled: added that the 35-day usage log is the only hard limit, since a rollback from new_only needs events that age out at day 35 (Q13).
- Day 35: stated that a new-engine failure rate above 2 percent in retired starts no rollback, and that the response is open (Q15).
- Shadow mismatch and open questions: corrected a contradiction. The old open question said the diagram reads 0.1 percent as a 7-day window, but the diagram and the failure notes read it per day. The open question now says the file reads it per day and asks for confirmation.
- Open questions: added the questions on resolving a both-mode mismatch, who is told of an automatic rollback, RB2 and RB3 running without a person, the decommission owner, and the failure response in retired. Kept the other open questions. The 7-day and 14-day counter and Finance sign-off notes are unchanged.
- Who does what: no change in substance. The controller still only starts RB1, and whether RB2 and RB3 run without a person is listed as open.
- Modes, both: added the charge order (charge sent, provider answers, then ledger written) and the idempotency key on each charge (Q16).
- Modes, new_only: the file now says it counts the 35-day clock from entry, and points to the open question, since the brief does not say (Q21 and open questions).
- Who does what: the person approves each forward move; the controller refuses a rollback from new_only that starts after day 35 (Q21).
- Rollback: added that billing_mode stays unchanged until RB3 finishes, and what customers and engines see during RB1 and RB2 (Q22).
- RB2: named the two sources, the usage event log and the shadow store, for the old engine's recomputed invoices (Q18).
- RB3: the old engine writes its charges to the ledger and leaves the new engine's rows unchanged (Q19).
- What happens when something fails: added that the approval mechanism and the detection of a failed ledger write are open (Q17, Q20).
- Open questions: added what starts a charge run, whether the flag alone stops the new engine, how a forward move is enforced, how on-call starts a rollback, and who notices a failed ledger write (Q16, Q17, Q20, Q21, Q22).

### Holes
- Q2: When someone sets billing_mode, how do the old and new engines learn about it? Do they read the config service on every run, or is it pushed to them? (author: The brief does not say whether the engines read billing_mode on every run or receive it pushed. Listed under open questions.)
- Q4: What measures the new-engine charge failure rate, and what counts as a failure (declined card, provider error, timeout)? Who or what triggers the automatic rollback when the 2 percent is crossed? (author: The brief does not say how the 2 percent charge failure rate is measured or which outcomes count as failures, including declines versus provider errors and timeouts. Listed under open questions, with the risk that declines could trigger rollback.)
- Q10: What does it mean for a mismatch to be resolved, and who resolves it? Does a new mismatch in both reset the 14-day count the way it resets the 7-day streak in shadow? (author: The brief says no unresolved mismatches, but does not define resolved, who resolves a mismatch, or whether a new mismatch restarts the 14-day count. The file now states only that the gate needs no open mismatch when a person approves. This is listed under open questions.)
- Q14: After the automatic rollback starts, who is told, and does on-call have to do anything for RB2 and RB3 to run? Or do they run on their own? (author: The brief says the controller starts RB1 on its own. It does not say who is told when that happens, or whether RB2 and RB3 run without a person. The file does not decide this. It is listed under open questions.)
- Q17: The text says a charge can succeed but the ledger write fail, or the reverse. Who or what notices that, and does it happen as a routine check or only during rollback? (author: The brief does not say whether a charge that succeeded with a failed ledger write is noticed by a routine check or only during rollback. The file's rule is the provider lookup by key, which applies either way. Detection is listed under open questions.)
- Q20: Who sets billing_mode to shadow at the start, and how does the controller know a person has 'approved'? Is approval a button, a command, or a config change? (author: The brief says a person makes forward moves, but not how the change is made or how approval is recorded. Whether approval is a button, a command or a config change is not in the brief. The file also has a gap: it says the controller refuses a forward move, but nothing stops someone from setting billing_mode directly. Both are listed under open questions.)
