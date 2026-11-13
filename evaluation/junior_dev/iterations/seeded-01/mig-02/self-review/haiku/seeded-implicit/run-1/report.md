## Review of mig-02 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Added a plain-language label to every transition in the Mermaid diagram (gate conditions, manual or monitor triggers, the 35-day decommission rule, and gate reset), which were previously only in the notes.
- Changed the new_only to decommissioned arrow to show its condition: 35 days in new_only with no rollback.
- Labelled the rolling_back to old_only arrow with 'gates reset', so the reset is visible in the diagram.
- Restructured the notes into separate sections: pieces involved, what each mode does, forward gates, rollback, the 35-day limit, and failures.
- Defined each piece (rollout tool, billing monitor, comparison job, comparison_results, shadow store, ledger, usage event log, rollback record) in one line each, for a reader who does not know the project.
- Explained what reconcile protects against, namely double charges and dropped charges, and why catch-up applies only from new_only.
- Explained why the 35-day limit exists, namely the usage event log's retention.
- Stated the failure behaviour in one place. The inferred details are: the roles of comparison_results, the shadow store and the rollback record are read from their names and the brief, not stated exactly; the 35-day count is assumed to start on entering new_only; and the note that a rollback can be retried is taken from the brief's 'steps are retryable'. Confirm these with the author before building the controller.
- Added a short "Key terms" section defining usage event, invoice, charge, ledger and shadow store, so a reader new to the project can follow the rest.
- Added a "Where the state lives" section that lists the mode flag, rollback record, comparison results, invoices, and usage events in one place, as the brief asks.
- Defined a mismatch in the mode descriptions and the gates as a per-customer invoice difference above one cent.
- Rewrote the mode descriptions in plainer language. Shadow now says the old engine keeps doing everything it did in old_only.
- Stated that a failed day breaks the 7-day streak, which is what "consecutive" means.
- Clarified in the rollback section that the diagram shows every step and that unneeded steps are skipped, with the shadow-rollback example moved there.
- Stated that a retry resumes from the failed step, using the rollback record's record of finished steps.
- Clarified the 35-day rule: on-call's manual rollback must happen within the 35-day limit, and the count starts when the rollout enters new_only.
- Split the failure notes into one bullet per case and stated that a shadow-mode rollback is never automatic. The diagram and mode text were otherwise left as they were.
- Added a short opening that says what the rollout is and what "rollback" means, so a reader new to the project can follow it.
- Defined the terms the document relies on but did not explain: mismatch, mismatch rate, and charge failure rate.
- Added a short "How to read the diagram" paragraph that explains the arrows and the rollback path.
- Clarified that catch-up is skipped for rollbacks from both as well as from shadow, since the old engine also computes every invoice in both mode. The earlier text named only shadow.
- Stated the gate as a condition that must be met before a forward move, and said that a move happens only when its gate is met.
- Changed the shadow mode description to say mismatches are recorded, rather than repeating the full comparison rule, which is already defined under key terms.
- Added an explicit open question: the brief does not say whether the billing_mode flag holds rolling_back during a rollback.
- Kept the Mermaid diagram, the section headings, and all rules and numbers unchanged.

### Holes
- None.
