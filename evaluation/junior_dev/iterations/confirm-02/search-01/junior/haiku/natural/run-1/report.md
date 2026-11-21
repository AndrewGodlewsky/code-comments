## Review of search-01 (junior, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Key decisions, lag bullet: defined lag as now minus the commit time of the last applied event, and said it falls under 5 s only at the live end of the topic (Q7).
- Notes: added a line that products-live and products-rebuild-v4 read the same topic with separate offsets per consumer group (Q8).
- Notes: added a line on how the per-partition offset commit interacts with transient retries and replay (Q9).
- Added an Open questions section: where rebuild progress (control records) is stored and who reads it (Q5), and who runs the cron cutover plus the unversioned cron-write gap (Q6).
- Cutover node: added step 0, pointing the connector at catalog-primary, slot search_slot and topic catalog.products, running at least 20 minutes before the cron stop (Q10). Replaced the claim that versions keep older replays from winning with a pointer to the open questions (Q12).
- Live decision node: the label now reads op is d (use id), or after.status is not active, so a delete does not look for status (Q11).
- Replay offset node: added why the offset is recorded before the snapshot (Q14).
- Snapshot version S bullet: added that S and commit_lsn are both WAL positions on catalog-primary, so they compare directly (Q13).
- DLQ write failure path: it now retries only the DLQ write, keeps the partition paused, and does not call the index again for that item. It no longer goes back through the bulk retry (Q15). Failure notes updated to match.
- Metrics node: added the share formula for the 95%-within-5-s gate (Q16).
- Rebuild stream node: says the slot is created before S if it was dropped, which covers changes committed after the drop (Q17).
- Open questions: the cron question now also asks what the store does with a versioned write over an unversioned document (Q12). Added two open questions: the in-flight commit race at the snapshot start (Q13), and the measurement window for the 95% share (Q16).
- Summary cut to three short paragraphs. It now says how today's cron works first, then the new flow and why it is shaped that way, instead of restating the diagram.
- Added a Terms section before the diagram, defining alias, version, WAL, LSN, replication slot, Debezium, topic, consumer group, offset, DLQ, snapshot, S, control record and stale event. Removed nothing from the brief's terms.
- Moved the one-time cutover out of the diagram into a separate Rollout section, so the diagram shows only how the system runs. Kept the 20-minute reason. Added step 0, repointing the connector, as decided in round 2, and noted that its owner is not stated.
- Merged the first version's Key decisions bullets into two sections: Rules for the live path and Rebuild path. Each fact now appears once. Removed the duplicate restatement of the failure notes in favour of one failure table.
- Diagram: shortened node labels, kept every branch, and gave each failure its own path, including the DLQ write failing and the expired replay offsets. Removed the old diagram's separate cutover node. Replaced the percent symbols with the word percent so the Mermaid parses cleanly.
- Rebuild path: added that an operator starts the rebuild, and that the slot is created before S so the gap after an ops slot drop is covered. Kept the 5000 rows/s, 2.5-hour and vacuum facts.
- Gate and switch: kept the three switch conditions, the 200,000-document slack, the weak count gate, the one-request alias swap, the 48-hour window and the rollback caveat.
- Failure table: merged the brief's failure rules and the first version's notes into one table. Kept the 20 GB and 50 GB WAL thresholds, the 1 s to 60 s backoff, the DLQ fields, the snapshot crash rule and the checkpoint being for monitoring only.
- Open questions gathered and reduced to the real unknowns from the answers: control record storage, cutover and connector owners, unversioned cron documents, the snapshot visibility race, the SLO window, the rebuild group name, and the Kafka timestamp assumption. Removed the 'version rule protects older replays' claim, which the round-2 answer said was not verified.
- Kept all brief facts: 95 percent within 5 s, commit_lsn versions, version conflicts counted not errors, offsets committed only after ack, the search rule for active rows, the 40 million rows and 300 writes per second, alias-only search, and the 0.5 percent count gate. Length is roughly one times the first version.

### Holes
- Q5: What are 'control records', where are they stored, and who reads them to decide the rebuild state? (author: The brief does not define control records, does not say where they are stored, and does not say who reads them. The draft introduced the term. The brief does require the diagram to show where progress is stored, and that is not decided. Added as an open question.)
- Q12: Cron writes documents with no version. When the replay then writes a versioned doc over one, what does the store do, and what is the actual risk you call a gap? (author: The brief and search-setup.md do not say what the store does when a versioned write hits a document that was written without a version. The earlier claim that the version rule protects against older replays was not verified, so the file no longer states it. The risk: a replayed older event (committed before cron's write) can overwrite the newer state cron wrote, and the stale value stays until the product changes again. Added as an open question.)
- Q13: The snapshot writes every document with version S. A live event for a row arrives later with an LSN above S. Why is its LSN guaranteed to be comparable to S, and what if a row changed between S and when the snapshot reader reads it? (author: The LSNs are comparable because S and each commit_lsn are WAL positions on catalog-primary, so they order directly. For a row that changes after S: the snapshot shows the row as it was when the snapshot started, and a change committed after that has an LSN above S and applies on top. Not verified: a commit whose WAL record lies below S but which only becomes visible after the snapshot starts may be missing from the snapshot, and its event is then stale under the version rule. Added as an open question.)
