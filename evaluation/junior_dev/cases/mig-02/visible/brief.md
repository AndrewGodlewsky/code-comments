**Billing engine rollout: model the state machine**

We are replacing the old billing engine with a new one. The switch must be gradual and reversible, and it must never charge a customer twice. Before anyone writes the rollout controller, I want the rollout modelled as a state machine.

**Today.** Billing workers run the old engine. They read usage events from the usage event log (kept for 35 days), compute invoices, write them to the billing ledger (the system of record) and charge customers through the payment provider.

**Fixed rules**

- One global flag, `billing_mode`, in the config service, selects the mode: `old_only`, `shadow`, `both`, `new_only`. Forward moves go one step at a time in that order, with no skipping, and a person always makes them.
- `old_only`: the old engine does everything. The new engine is off.
- `shadow`: the old engine still charges and writes the ledger. The new engine reads the same usage events and writes its invoices to a separate shadow store. It never charges and never writes the ledger. A nightly job compares the two engines' invoices per customer. A mismatch is any invoice total that differs by more than one cent.
- `shadow` -> `both` requires 7 consecutive days with a mismatch rate under 0.1% and at least 5,000 invoices compared.
- `both`: the new engine charges and writes the ledger. The old engine keeps computing every invoice into the shadow store without charging, so it stays current. The comparison continues.
- `both` -> `new_only` requires 14 days in `both` with no unresolved mismatches, plus Finance sign-off.
- `new_only`: the old engine stops computing.
- Rollback can start from `shadow`, `both` or `new_only` and always ends in `old_only`. On-call can start it by hand at any time, within the 35-day limit below. It starts automatically when, in `both` or `new_only`, the new engine's charge failure rate is above 2% over any 10-minute window. New-engine errors in `shadow` are recorded but never trigger a rollback.
- A rollback must not charge anyone twice for a billing period, and it must not drop a charge that is due.
- Rolling back from `new_only` means the old engine must first reprocess the usage events it skipped. The old engine may be decommissioned after 35 days in `new_only` without a rollback. From day 35 on there is no way back.
- After any rollback the gates reset: the rollout goes through `shadow` again and its 7-day count starts over.

**Format.** Give me a Mermaid `stateDiagram-v2` of the modes and transitions, including the rollback path and its steps. Add short notes before or after it that say what each mode does, where the rollout state lives, and what happens when something fails.
