## Review of mig-02 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added an overview that states the goal and the two core rules (no double charge, no dropped due charge) before the diagram.
- Added a short glossary for usage event log, ledger, charge key, shadow store, fence and reconciliation, so a reader outside the project can follow the document.
- Rewrote the diagram labels to be plainer. The shadow-to-old_only edge now says no charges to settle, and the both-to-rollback edge now says manual, or automatic when charge failures exceed 2 percent in a 10-minute window. Otherwise the states and transitions are unchanged.
- Changed the new_only replay reconciliation label to say the ledger marks already-charged periods as closed, which says what the step does for the old engine.
- Turned the rollback composite descriptions into numbered step lists for shadow, both and new_only. Each list names the fence, settle, replay (new_only only), reconcile and final flag-set steps.
- Explained the purpose of the 'does not count as clean' rule and the streak effect in the gates section.
- Added an open point asking whether a day that cannot count as clean pauses or resets the streak. The source text said the streak does not advance but did not say whether it resets, so this is a real ambiguity.
- Clarified the new_only expiry rule. Skipped events expire 35 days after they were created, which is separate from the 35-day decommission clock, and the replay must finish well before that.
- Kept the section structure, the Mermaid stateDiagram-v2 format, the open points and all rules and thresholds unchanged.
- Overview: explained in plain words what the old and new engines are and what the flag controls, before using the terms.
- Added a Terms section defining billing period, invoice, gate and the other terms the document uses, so a reader outside the project can follow it.
- Diagram: added a short paragraph explaining how to read the arrows and the Rollback boxes, including that they are controller steps rather than flag values. The Mermaid code itself is unchanged.
- Mode descriptions: replaced 'totals' and 'computes' wording with 'invoice totals' and 'results' where the meaning was vague, and stated the one-cent mismatch rule in full.
- Rollback steps: stated up front that rollback can start from shadow, both or new_only and always ends in old_only, and numbered the steps consistently.
- Gates and safety rules: tightened sentences so each rule has one meaning. Kept all the rules and the open points as written; no rule was added, removed or changed in substance.
- Where state lives: turned the rollout-record fields into a list so the contents are easy to scan.
- Defined payment provider, usage event log, billing period, and settle, and explained why the charge key is the safety mechanism.
- Explained the relationship between the 35-day rollout clock and the 35-day expiry of each usage event: a skipped event is always created after entry into new_only, so the clock and the expiry line up.
- Rewrote the diagram reading note to separate forward moves (person-approved), the way back into old_only, and the rollback boxes, which are step sequences rather than flag values. Stated that the flag still reads both or new_only while fenced.
- Shortened and simplified sentences throughout, including the mode descriptions, the failure list, and the gate rules. Merged the repeated shadow-mode error statement into one place.
- Clarified that a day that cannot be checked does not count as clean and does not advance the streak. Left the diagram structure and the open points unchanged.

### Holes
- None.
