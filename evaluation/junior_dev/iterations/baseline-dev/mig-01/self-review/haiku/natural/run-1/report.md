## Review of mig-01 (self-review, author haiku, natural)

Rounds: 3. Ended: passes.

### What changed
- Added a one-paragraph overview under the title so a reader knows the goal before the details.
- Added a Terms section defining source, mirror, version, outbox, repairer, verifier, guarded copy, tombstone, control row, epoch and procedure S, since the document uses them throughout.
- Explained why pauses use the control row instead of a flag, in plain terms (flags refresh every 30 s).
- Procedure S: made explicit that the pause update waits for in-flight writes to commit and that max_outbox_id is read after that commit. The original left this implicit.
- Procedure S: stated the abort rule and the roll-forward rule more plainly, and gave the pause budget as a simple sum.
- Design decisions: stated that a missing source row during repair means the other store must be erased, which the original implied but did not say.
- Design decisions: described the guarded copy as an ordered list of steps (lock, tombstone check, insert or version-checked replace).
- Added source_changed_at to the step 0 table list, since steps 8 and 11 use it, and set its timing to procedure S step 6.
- Step 2: replaced the ambiguous 'once step 4 has started' with 'once backfill (step 4) has started', and corrected the claim that flag-off writes can never be repaired. The verifier would find them later.
- Step 0: stated that the new tables are additive only, and that the monitoring thresholds for the step 8 and 10 gates are set here.
- Step 0: explained what the no-raw-users-sql lint rule is and why the repairer, backfill and verifier are exempted by file name.
- Step 11: rewritten as procedure S with Postgres as both old and new source. Steps 3 and 5 are skipped, and mirror = off is set at the commit point. The original put this in step 4 with no explanation.
- Step 12: stated that the MySQL migration tables are dropped, and that Postgres keeps the tombstones.
- Open questions: added that the outbox threshold for step 8 is not yet set.
- Added a Replica entry and a Lease entry to Terms, and an Idempotent entry, so a reader new to MySQL, Postgres and the job design can follow the text.
- Moved the explanation of the guarded copy to Design decisions and gave its steps as a numbered list, so Terms can point to it without using a term before it is defined.
- Explained the shared and exclusive locks on the control row and why a pause waits for in-flight writes.
- Explained why instances disagree on flags and why pauses and switches use control rows instead of flags.
- Turned the procedure S abort and roll-forward rules into a short bullet list, and named old source and new source at the start of the procedure.
- Simplified the write check and pause budget paragraphs without changing their limits or rules.
- Step 2: explained why the flag must stay on once backfill starts, in terms of what a write made with the flag off would miss.
- Step 11: explained that steps 3 and 5 of procedure S are skipped because the store does not change, and that mirror = off is set in the step 4 commit.
- Step 10 and step 8: named which procedure S step is meant (step 6 of procedure S, and before step 1 of procedure S) to remove ambiguity with the checklist's own step numbers.
- Rewrote list items in plainer language (for example, Stops if it has lost the lease, sleeps 1 s) without changing any behaviour, and kept all numbers, gates, limits and open questions unchanged.
- Added a short plain-language overview with the three phases (mirror, switch, finish) before the terms, so a reader sees the whole plan first.
- Expanded the terms list: 'guarded copy' now says it is the one operation for every write into a store, and 'replica', 'lease' and 'idempotent' are explained in plain words.
- Explained why the outbox is in the source database and why it is not app.jobs, in plainer sentences.
- Rewrote the guarded-copy steps as a numbered list, with the Postgres and MySQL statements moved to a follow-on sentence.
- Explained the control-row locking in plain terms: shared locks for writes, exclusive lock for a pause, and why flags were rejected.
- Procedure S: stated the six steps as a numbered list and clarified that after step 4 the procedure only rolls forward. Made the 'pause budget' sentence explicit.
- In the checklist, replaced 'Starts when' wording with the same conditions in simpler sentences and fixed small wording issues (for example, the lease renewal and the MySQL time-zone check).
- Step 10 now says why AUTO_INCREMENT must be checked, in one sentence.
- Step 12 now makes clear that the Postgres tombstones are kept, while the MySQL tombstone table is dropped.
- Open questions: kept all items unchanged in substance, with shorter sentences. No requirements, numbers or gates were changed.

### Holes
- None.
