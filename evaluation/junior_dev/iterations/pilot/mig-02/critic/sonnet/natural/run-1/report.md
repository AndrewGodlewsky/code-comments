## Review of mig-02 (critic, author sonnet, natural)

Rounds: 3. Ended: cap.

### What changed
- Added a 'During a rollback' table defining who charges, comparison job, counters and forward-move behaviour while the flag still shows the origin mode (point 1).
- Defined the day-35 boundary: rollback can start while under 35 days, rollback_closed_at is set at 35 days, and an in-flight rollback completes (point 2).
- Decided the retention hole: pin usage events as a precondition of the new_only move and reprocess from the pinned archive; added a missing-events path to Blocked (point 3).
- Capped Reprocess retries at 5 with backoff, then Blocked and a page; Blocked now returns to the step it came from (point 4).
- Simplified shadow rollback to a direct edge to old_only with no Freeze/Switch; added compare-and-set on a versioned rollout record to resolve races; auto triggers and forward moves during a rollback are ignored or rejected (point 5).
- Decided the failure-rate rule: failed over total attempts, sliding 10-minute window, minimum 200 attempts, card declines excluded, flagged as proposed defaults for on-call to confirm (point 6).
- Fixed the mode table by adding a shadow-store writer column and stating the new engine's shadow behaviour consistently; added one Counter resets table for G1 and G2 (point 7).
- Removed the new_only_locked and old_engine_decommissioned states in favour of a rollback_closed_at field and a single decommission edge; made the old_only re-entry an explicit edge; split open questions into blocking items with owners and non-blocking confirmations (point 8).
- Point 1: Defined rollback_closed_at as new_only_entered_at + 35 days, written at the move to new_only. No timer sets it. Eligibility is a time test inside the rollback-start compare-and-set, so there is no undefined gap at day 35.
- Point 2: Added flag semantics to the diagram edges (flag unchanged until Switch, flag set to old_only, counters reset, resumes and charges queued periods). Made Reprocess unconditional from both and new_only, so the diagram no longer hides a branch in the text. Added a note that the diagram is authoritative for transitions, and trimmed duplicated prose.
- Point 3: Added a definition of the shadow store (the non-authoritative engine's invoices, never charged). Added a 'How queued periods are charged' rule for how shadow invoices reach the ledger (promotion only for periods with no ledger entry, with the idempotency key).
- Point 4: Stated that the ledger invoice is authoritative and, in both, the new engine's. Changed the mode table column to 'Authoritative invoice (ledger) written by'. Specified that existing ledger invoices stand during rollback. Added open question 4 for confirming this.
- Point 5: Gave Blocked an escalation ladder (re-page every 30 minutes, secondary after 1 hour, billing lead and Finance after 4 hours, 24-hour target). Said that the archive, the live log and decommission are held while blocked, including past day 35. Added the failure-table rows and open question 2.
- Point 6: Spelled out archive retention (until a rollback completes or decommission). Decommission is allowed only after rollback_closed_at and with no rollback in progress, enforced by compare-and-set. A rollback in progress at day 35 or later is explicitly covered.
- Point 7: Stated the 2% threshold in the Auto-rollback section. Added a low-volume fallback (rate above 2% with at least 10 system failures, plus a page on zero successes). Listed it in open question 1.
- Point 8: Split the counter table into reset rules and gate conditions, and removed the non-reset rows. Defined qualifying days for G1, including missed job runs and zero invoices, and how the 5,000 total behaves (a condition, not a reset).
- Point 8, staleness: Removed the assumption that the old engine is current in both by making Reprocess run from the old engine's watermark in every rollback. Moved the staleness alert from blocking to non-blocking and renumbered the open questions.
- Summary and shadow handling: named the shadow path a 'shadow exit', a separate manual step with no procedure, distinct from Rollback (both/new_only only); stated once and used consistently, and the diagram label and 'one exit' line now match.
- Diagram: labelled both Rollback entries with the source mode stored in the record, relabelled Freeze, made Reprocess-to-Reconcile say 'immediate if already current', and added a Blocked note carrying the escalation. Narrowed the authority claim: diagram governs states and transitions, prose governs numbers and timings.
- Clarified shadow store vs ledger: it holds the non-authoritative engine's invoices, and the old engine's copy in `both` is what can be promoted during rollback. Marked the promotion rule as unapproved with a stated fallback (those periods go to Blocked) and fixed the cross-reference to open question 4.
- Renumbered open questions: gate definitions (G1 volume, G2 wording) and decommission now sit in the blocking group; only the staleness alert is non-blocking; removed the claim that they are 'diagram readings'.
- Archive retention rewritten as one rule: held from pin until Switch of a completed rollback (even after day 35) or decommission, held while Blocked, with a day-35 and monthly page to billing engineering so storage cost is not forgotten.
- G1 made precise: one consecutive run, any non-qualifying day resets it, a short 5,000 total does not reset but moves the 7-day window forward. Removed the contradictory 'recomputed' wording. Defined open mismatch (what opens and closes it) and tied it to G2; stated that 0.1% does not apply to G2.
- Auto-rollback simplified to one rule: rate above 2% and at least 10 system failures. Dropped the 200-attempt floor and the zero-success rule (now a page-only case below the minimum). Stated that 10 failures in 12 attempts fires, and that requests during a rollback get an explicit rejection and a log, not silent ignore.
- Reduced redundancy: single-rollback, deadline, compare-and-set and Blocked rules now stated once; the failure table is an index; merged 'During a rollback' into the Rollback section; Summary now says moves require gates and sign-off.

### Holes
- None.
