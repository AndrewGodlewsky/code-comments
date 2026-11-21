## Review of ms-02 (junior-v2, author sonnet, natural)

Rounds: 1. Ended: teachback-correct.

### What changed
- Components table and ownership rules: added the Reconciler row, stated that flags.get is read fresh on every poll, and stated that monolith failed is only a record (Q1, Q5, Q6).
- Messages: added one line saying what ack means and that an unacked message is redelivered after 30 s (Q3).
- Step 3 worker rule: added rule 5, guarding every update with status='pending' and the worker's own lease value, and noted that duplicate sends from an expired lease are absorbed by the key (Q4).
- Step 4: added the batch size of 50 and per-row handling of unconfirmed publishes, the reconciler's location, frequency, publish-only behavior and the 15 min versus 60 min reasoning, and a dashboards-and-alerts bullet built in this step (Q2, Q6, Q8).
- Step 6 exit criteria: now say they are read from the step 4 dashboards (Q8).
- Break-glass rollback: added that the service is not told, and that its late sends and results are neutralized by the key and the status check (Q7).
- Open questions: added the broker product and push versus pull, and MailRelay's send timeout (Q3, Q4).
- Cut the break-glass 'service is dead' procedure (operator resets handed_off rows to pending); the brief only requires a flag-flip rollback, so this extra mechanism and its 12 h / 24 h window rules are gone.
- Removed the 'Earliest timeline' table, which repeated the day numbers already in each step heading.
- Merged the three 'safety layers' and rollback 'why safe' bullets into shorter statements; merged the duplicate flag-reading bullets into one ownership bullet.
- Merged the separate rollback drill paragraph into the step 5 drill list.
- Dropped detail the main flow does not need: 'Publishing happens while row locks are held', redundant 'one-time transient' exit line in step 1, the separate Exit line in step 1, the NTP-skew and version-verification elaborations, and the 'Do not rely on the key' remark in step 2.
- Folded step 9's duplicate 'drop old worker code only after last pending row' bullets into one condition on the removal list.
- Trimmed failure bullets to one line each and kept all open questions together at the end.

### Holes
- Q3: What is the broker here, and how does the consumer receive messages (push or pull)? What does 'ack' do, and what is the 30 s before redelivery measured from? (author: The docs only say it is the platform broker already used by billing and search, at-least-once, with an unacked message redelivered after 30 s and publisher store confirmations. The product, push versus pull, and exactly what the 30 s is measured from (presumably delivery) are not known. Ack means the consumer is done with the message. The plan does not depend on push or pull. Added to open questions.)
- Q8: How does an operator see the exit-criteria numbers (pending or handed_off over 30 min, count reconciliation)? Are these dashboards and alerts that already exist, or are they built as part of this plan? (author: I do not know whether such dashboards exist. The plan now builds them in step 4: per-type counts and oldest age of pending and handed_off, failed count, and the reconciler alert. The two databases cannot be joined, so count reconciliation is a side-by-side comparison of the monolith and service dashboards.)
