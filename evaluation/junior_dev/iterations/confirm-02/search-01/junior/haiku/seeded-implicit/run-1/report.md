## Review of search-01 (junior, author haiku, seeded-implicit)

Rounds: 3. Ended: teachback-correct.

### What changed
- Rewrote the whole plan for a newcomer: a summary, a terms list, the Mermaid flowchart, numbered steps for the live path and the rebuild, a failure table, rollout notes and open questions.
- Added a second indexer consumer group per target index (group-v3 and group-v4), so v3 keeps receiving changes after the switch and rollback loses nothing.
- Defined the event contents, the rule for draft and archived rows (delete from index), and delete handling.
- Set the backfill version to the snapshot WAL position S, and the catch-up start to the offsets recorded before the snapshot, so overlap is handled by the version rule.
- Restored every brief requirement that the first version had dropped or left implicit: retry timing (1 s doubling, capped at 60 s, never skip), offsets committed only after acknowledgement, the DLQ with error and alert, WAL alerts at 20 GB and 50 GB, the two rebuild gates, the 48-hour window, and the cron retirement.
- Cut repetition: the search rule, the retry rule and the WAL rule each appear in one place.
- The file is longer than 1.5 times the first version, because the brief's stated facts had to be kept.
- Added a summary before the terms, and the terms come before the diagram, as diagram form requires.
- Defined in the terms: lag (zero on an idle topic), settled, S, the DLQ, the snapshot, and the one search cluster. Kept the 300 writes/s peak and the 40 million rows.
- Diagram: added the progress record, the job-crash restart path, the offsets recorded before the snapshot, the lag-based gate, and the rollback arrow to the alias.
- Step 9: the offsets are recorded before the snapshot, and the order is explained in one place. S and the offsets are saved in the progress record.
- Step 10: the backfill saves the last id after each batch, so a restart can resume.
- Step 11: a backfill row older than an applied change is refused. Deletes after S are marked as the exception, tied to the rollout precondition.
- Step 12: the gate uses the lag definition, and a failed count gate after backfill alerts an operator.
- Rollout: Debezium's own initial snapshot is turned off, and a precondition requires the store to keep deleted-document versions for the backfill time before any rebuild. The group-v3 start point is set to the step 9 offsets.
- Failure table: the restart path uses a new snapshot and S, and group-v4 keeps its committed offsets. The DLQ replay and gate rows say who acts and when.
- Merged the repeated write rules into step 3 only, and cut the duplicate notes about the diagram. Open questions gained the cron-gap option and the connector initial-snapshot question.
- Step 8: added the restart rule. If a progress record for products_v4 exists, the job resumes with a new snapshot instead of creating the index again (Q19).
- Step 9: named the reindex job as the owner of the progress record, and kept its storage as an open question (Q19).
- Step 11: replaced the one-line exception with the outcomes of a race between a change and a backfill write: a newer change wins, a delete after the backfill removes the row, and a stale event below S is refused (Q17, Q18).
- Step 13: stated that the gates are checked just before the move and not re-checked, why that is safe, and that group-v3 is not a gate but must run for the 48-hour rollback (Q21).
- Rollout: added that group-v3 does not run before the first switch, so no versioned write touches a cron-written document until then (Q20).
- Open questions: rewrote the active row count item. The snapshot count is right only at S, so the count gate needs a live count whose method is unknown (Q22).
- No other step changed; the diagram, terms, live steps and failure table are unchanged in this round.
- Summary cut to one paragraph that says how the cron works today and what the new design changes, with no repeated steps.
- Terms section expanded to define every name a newcomer would not know: CDC, WAL, slot, Debezium, topic and partitions, offset, consumer group, version, version conflict, snapshot, S, settled, DLQ, lag, gate, active row, alias and progress record. Also stated the event contents (whole row, no old values) and that one transaction's rows share a commit_lsn.
- Diagram kept in Mermaid flowchart form, with all nodes from the first draft. Labels shortened. The progress record now has three explicit save arrows (offsets, S, last id) and a restart arrow back to the snapshot. Summary and terms placed before it; notes placed after it.
- Added notes after the diagram: live path always on, rebuild touches the alias only at the switch, step 3 rules apply to both groups, and the accepted partial-visibility effect of one transaction across products.
- Live steps: the three decide-per-event rules merged into one list under step 3. Retry, DLQ and offset-commit rules kept as written. Step 1 now says where the WAL is kept.
- Rebuild step 9: kept the offset-then-snapshot order and the reason for it in one sentence.
- Rebuild step 11: all four outcomes for a row written by both paths kept, including the stale-delete restore case and the unknown exception. Added the restart rule that group-v4 uses its own committed offsets, from the earlier answers.
- Steps 12 and 13: gate check and switch kept. Stated that the gates are checked once before the move, with no manual step and no re-check. Moved the alert and the count-gap causes into the failure table so they are not repeated.
- Failure table: every row from the first draft kept. Added the causes of a count gap and the restart detail for the reindex job, including that rows written before a crash keep their older S.
- Rollout moved to its own section, apart from how the system runs. All five rollout items kept.
- Open questions: every question from the first draft kept, with the unknown answers and the count-gate method, cleanup and cron points kept as they were. Added the unknown about how the store treats versioned writes over cron-written unversioned documents. Added one new open question on how a text commit_lsn such as 0/16B3748 becomes a comparable version. This was not raised by the junior and is flagged for the author to verify.
- Length is above the target of about 1.5 times the first version. This is deliberate. The first version left out many facts the brief states, and the skill's rule against cutting stated facts takes priority over length.

### Holes
- Q9: The backfill writes each row with version = S, but a live event after S has commit_lsn larger than S. If a row is deleted or made inactive after S, is the delete event always applied after the backfill wrote it? What if the backfill writes that row later than the delete event was applied? (author: Not known. The backfill writes a row with version S. A delete or deactivation after S has a larger commit_lsn. If the delete is applied first, the backfill write is accepted only if the store still remembers the deleted version, and the brief does not say whether it does. If the store forgets, a deleted product can come back. The file now requires confirming this before a rebuild starts, and it stays an open question.)
- Q20: The cron currently writes products_v3 without versions. Between now and the first switch, who keeps products_v3 up to date, and what happens to the cron's data if a versioned write from group-v3 meets a document the cron wrote earlier? (author: Until the first switch, the cron is the only writer of products_v3, and group-v3 does not run before then, so no versioned write meets its documents (rollout updated). What the store does when the first versioned write lands on a document the cron wrote without a version is not known, because the brief does not say how the store treats unversioned documents. That is already listed in Open questions.)
- Q22: How is the 'active row count' for the count gate taken from the primary, and how does the job know the count of documents in products_v4 is comparable, given that some documents are in the DLQ and writes are still arriving? (author: The brief names no cheap way to take a live active row count from the primary. A count read inside the snapshot is right only at S, because changes after S move the primary and products_v4 but not that count, so it cannot be compared to products_v4 directly. The DLQ size is countable, so the DLQ gap is known. How to take the live count, and whether the 0.5% gap still holds after a long catch-up, is not known (Open questions updated).)
