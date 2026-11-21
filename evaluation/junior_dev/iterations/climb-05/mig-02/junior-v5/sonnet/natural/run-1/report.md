## Review of mig-02 (junior-v5, author sonnet, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Added a Terms section defining usage event log, billing ledger, shadow store, payment provider, config service, gate and promote, because Q8 and Q1 showed these were assumed.
- Stated that RollingBack is a diagram state only and that billing_mode keeps its origin value until handover, which resolves the Q7 conflict with the one-flag rule.
- Changed reconcile_ledger: a recorded-but-not-made charge is marked not charged so the period stays due, an alert goes to on-call, and the rollback does not wait for a person. This fixes a dropped charge the old wording allowed (Q5).
- Defined in flight and who reads the lock in the pause_charging and drain_in_flight steps (Q3, Q4).
- Spelled out handover: the old engine recomputes and charges every period with no charged ledger entry, once (Q6).
- Said in the mode table that a comparison mismatch never blocks a charge, and said who computes the gate and how the person is notified (Q1, Q2).
- Added the silent payment provider to the rollback-step-fails row, and open questions 8, 9 and 10 for the lock polling speed, in-flight tracking and timeout, and how a person promotes.
- Added a Billing period term saying invoicing and charging happen once per closed period, and defined 'due'; flagged as an assumption (open question 11).
- Added a Charge failure term and described the charge monitor that writes the rollback record to start an automatic rollback (open question 12).
- Explained that new_only_committed is derived from the flag history (35 days in new_only) and that rollback requests are refused then.
- Ledger term now says entries are marked charged or not charged and that reprocessing and reconcile_ledger also write it; reprocessing writes entries marked not charged.
- reconcile_ledger now says the provider is queried by idempotency key and that a provider charge with no ledger entry is added as charged.
- Open question 6 now also covers a provider lookup by key; added open questions 11 and 12.
- Opened with a summary paragraph that says how the old engine works today, the main flow and why it is shaped that way.
- Added terms for Mismatch, Charge failure, Promote and Charge key. Config service now says it holds the rollback record too.
- Merged the double-charge rule into the Charge key term and the handover step, instead of a separate paragraph.
- Split the forward flow into numbered steps (gate check, promote, day 35) with what starts each, who acts and what happens on failure.
- Folded the nightly job and promotion text into the forward steps, and the two derived-state notes into short bullets after the diagram.
- Cut the 'Unknown' wording from the rollback notes and shortened step descriptions. Moved reprocessing to say it writes entries marked not charged.
- Merged failure rows: the committed-breach row and charge-breach row are kept, but wording is tightened. Removed the duplicate 'forward moves blocked' and 'after a rollback' repetition.
- Reduced open questions to short one-line items. Added question 10 (how a person promotes) in place of the long form, and kept all 12.
- Kept the diagram unchanged.

### Holes
- Q3: In pause_charging, who actually reads the rollback lock and stops charging? Do the old and new engine workers each poll the config service, and how quickly do they notice it? (author: The brief does not give a polling interval. I decided that every charging worker, old or new, reads the rollback record from the config service and starts no new charge while the lock is set. How quickly they notice is not known. I added it as an open question. drain_in_flight is the safety net for charges started just before a worker saw the lock.)
- Q9: What starts an invoice computation and a charge in normal running: a schedule at the end of each billing period, or each usage event? I need this to picture what 'charges that fall due now' means during the pause. (author: The brief does not say what triggers invoicing and charging. I assumed the old engine computes and charges each billing period once, after the period closes, not per usage event. A charge that 'falls due' during the pause is a period that closed and has no charged ledger entry. I added this to the Terms and as an open question.)
- Q10: What component measures the charge failure rate over a 10-minute window, and what counts as a failure (provider decline, error, timeout)? What does it do to start the rollback? (author: The brief names no component and no definition of a failure. I assumed a charge monitor counts charge attempts per 10-minute window, treats declines, errors and timeouts as failures, and when the rate is above 2% writes the rollback record (lock set, origin mode, step pause_charging), which starts the rollback runner. A manual start writes the same record. I added this to the rollback path and as an open question.)
- Q13: Where does reconcile_ledger get the provider's list of charges, and what does it do for a charge the provider shows that has no ledger entry at all, given the new engine may have crashed mid-charge? (author: The runner asks the payment provider for its charges by the (customer, billing_period) idempotency key. If the provider shows a charge with no ledger entry, for example after a crash mid-charge, reconcile adds the entry as charged, so the old engine does not charge it again. Whether the provider supports looking up charges by key is not known, so I added it to open question 6.)
