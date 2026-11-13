## Review of mig-02 (junior-v5, author haiku, natural)

Rounds: 5. Ended: teachback-correct.

### What changed
- Rewrote the summary to say first how the old engine works today, then how the main flow goes from start to finish.
- Added a terms section that defines the flag, rollout record, compare-and-set, controller, ledger, shadow store, key, ledger intent, idempotency key, mismatch, due and uncharged, and the five rollback steps.
- Added a sentence saying the controller is not designed yet, so readers know what performs the mode changes.
- Defined freeze concretely as a flag in the rollout record that both engines check before each charge, and said that billing_mode is not used for it. Marked this as a proposal.
- Rewrote the five rollback steps as one ordered list. Each step now says what starts it, what it does, which part keeps its data, and what happens when it fails.
- Added the reconcile rule for due and uncharged periods, and for ledger intents with no recorded result.
- Added a how-the-engines-compare-and-charge section, answering who decides which invoice is charged in both.
- Merged the duplicate failure lists into one failure table, and removed the repeated rule about retries being safe.
- Moved the build and rollout steps into their own section, separate from how the system runs.
- Moved the unresolved assumptions and decisions into open questions, including the approver, the controller schedule, the charge-failure definition, the shadow store after rollback, and the ledger intent fields.
- Kept the mermaid diagram as it was, so the modes and transitions are unchanged.
- Terms: the controller now only applies mode changes and runs the automatic trigger. A new nightly-job term owns writing the comparison results and gate counters to the record (answers Q14).
- Terms: added Resolved mismatch and Rollback origin, so the rollback steps and the both-to-new_only gate use defined words (Q12).
- Gate counters: moved the counting rules into their own short section, with the failed-night reset stated once.
- Forward moves: a move is refused while the record is RollingBack (Q15).
- Rollback start: a second start or trigger while RollingBack does nothing and is logged (Q15).
- Resume: a declined card is recorded as failed and counted as handled, with the retry left to existing billing terms. Provider errors are checked by key first (Q10).
- Reprocess: stated the day-35 deadline, and that a rollback still running at day 35 pages on-call and stays frozen (Q11).
- Reconcile: stated that it stays in place while the provider cannot answer (from the failure table).
- Nightly comparison keeps running during RollingBack, and the automatic trigger is ignored during RollingBack (Q13).
- Mode notes and the diagram: the new_only to new_only_locked transition now says no rollback is in progress, and the reprocess note no longer says 'skipped events' in a way that differs from the steps (Q11).
- Merged the duplicate 'How the two engines compare and charge' section into the mode notes, and cut the repeated rollback summary.
- Failure table: added rows for a second trigger, a refused forward move during rollback, a freeze that cannot be set, a provider that cannot answer, a declined card, and a rollback still running at day 35 (Q10, Q11, Q15).
- Open questions: added who tells customers and Finance, the day-35 rollback case, the retry key for a declined card, and who may mark a mismatch resolved (Q10, Q11, Q12, Q13).
- Terms: Controller now also advances the rollback steps. Shadow store defined as one store with a partition per engine.
- Where the rollout state lives: rollback step writes use compare-and-set and retry only while RollingBack; nightly job writes only counters (Q16). Shadow store keying and the nightly comparison across shadow store and ledger added (Q22).
- Forward moves step 3 and 4: record written first with compare-and-set, then billing_mode; a failed billing_mode write is retried (Q21, cross-store write).
- Rollback starts: billing_mode keeps the origin value until the final write in resume.
- Steps intro: the controller runs the steps in order and stores the current step in the record (Q17).
- Drain: in flight means a pending ledger intent; a timed-out or errored pending intent is unknown and queried by key (Q20).
- Reprocess: covers skipped events up to the time it runs, and its invoices are the amounts resume charges (Q18).
- Resume: not-yet-due periods are billed by the normal old_only run (Q19); final write order changed to billing_mode first, then one record compare-and-set, with the freeze held until that write succeeds (Q21).
- Failure table: new row for a failed final rollback write.
- Open questions: added the drain timeout, which the brief does not set.
- Forward move step 1 and Gate counters: state that the controller reads the counters the nightly job wrote and does not recount invoices (Q23).
- Rollback start: the start write now sets RollingBack, the origin and the freeze flag in one CAS, which closes the window before freeze (Q24).
- Day 35: the controller sets new_only_locked by a date check, and rollback start is refused from day 35 by date, not only by the lock (Q25).
- Resume: states where the amount comes from for origin both (shadow store) and origin new_only (reprocess output) (Q26).
- Reprocess: now runs in passes until a pass finds no new events, so events arriving during rollback are covered (Q27).
- Resume: adds a final reconcile pass before the final writes, so periods that fall due during rollback are charged by resume (Q28).
- Failure table: a step is failed when its call returns an error; a stuck step pages on-call; the time limit is an open question (Q29).
- Merged repeated rules on approvals, counter writes and retries in Where the rollout state lives, and removed the duplicate rollback-start text.
- Merged duplicate open questions (the 5,000-invoice question, the day-35 question, the freeze questions) and added the reprocess-pass and step-timeout questions.
- Shortened the diagram labels to plain words and moved the gate detail into the notes and forward moves, so the diagram stays readable.
- Resume: added the amount source for origin shadow. The old engine computes the period's invoice from usage events, and the list is usually short.
- Resume: the list excludes periods with a succeeded or declined row, and the final-pass loop adds only periods not on an earlier list. This stops a declined card from being listed or charged again and makes the loop end.
- Resume: a provider error or timeout retry reuses the same key, stated in the resume step.
- Drain: stated that in shadow the pending intents are the old engine's normal-run charges.
- Reconcile: a period with a declined row is not put on the resume list, consistent with the resume rule.
- Failure table: the declined-card row now says the period is not listed or retried in rollback.
- Open questions: the declined-card question now asks which key or attempt a later retry uses under the existing billing terms.
- Summary rewritten as one plain paragraph: how the system works today, the main flow from start to finish, and why it is shaped that way.
- Terms: every term a newcomer needs is defined in one plain line. Added definitions for the payment provider, compare-and-set (CAS), the idempotency key and the resolved mismatch. Dropped the duplicate rule text that sat under the terms.
- Diagram kept in Mermaid form, unchanged in its transitions, with the summary and terms placed before it and the notes placed after it.
- Mode notes merged with the 'where the state lives' rules. Conflict rules for CAS writes (approvals, nightly counters, rollback steps) are now one short list.
- Forward moves rewritten as five numbered steps, with the record-first then billing_mode order and the retry rule kept. Gate counter rules and the day-35 rule moved into their own short sections.
- Rollback start, freeze, drain, reconcile, reprocess and resume each rewritten as a step that says what starts it, what it does, where its state is kept and what happens when it fails. The origin-specific amount source for resume is stated in full. The final pass and the final-write order are kept as written.
- Failure table kept as one table; wording made plainer and the 'stuck step pages on-call' rule kept. Removed the cross-references that pointed the reader to other sections for a rule.
- Open questions kept in full, since each one records a gap that the plan does not decide. No open question was removed or merged.
- Cut: internal wording such as 'this was a real gap' and 'this replaces the earlier wording' is not in the file. Round references and change notes are kept out of the file and live in the report.

### Holes
- Q1: Who or what is "the person" who approves forward moves, and where do they approve (a UI, a command, a ticket)? What exactly happens in the system when they approve? (author: The brief says only that a person always makes forward moves. It does not name the person, the interface or the command, and no other file in the plan defines it. The plan does fix what the approval must carry: the record version the person saw. The controller applies the move only if that version still matches.)
- Q2: What is the "controller"? What process actually performs mode changes, updates the counters, and runs the automatic rollback trigger, and how often does it run? (author: The brief says the rollout controller is still to be written, so no process exists yet. How often it runs is not stated. The plan says what the controller does (apply mode changes, update counters, run the automatic trigger). It does not set a schedule.)
- Q3: How does the failure rate get measured? Where do the charge results come from, and what counts as a "charge failure" (declined card vs. provider error)? (author: The brief gives the 2 percent threshold and the 10-minute window. It does not say what counts as a charge failure (a declined card or a provider error) or where the charge results come from. The plan does not decide this.)
