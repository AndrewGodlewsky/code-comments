## Review of sync-01 (self-review, author haiku, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Rewrote the opening so it says where each piece of state lives (phone SQLite and outbox, server notes, change log, processed change IDs, cursor) and what each one holds, rather than listing the components in one line.
- Added a short glossary of version, base version, change ID, change log and cursor, so a reader who does not know the project can follow the rest.
- Expanded the sequence diagram so it shows the conflict copy being saved on the server, the conflict result returned to phone B, and phone B's download picking up both the winning change and the conflict note. Kept the same participants and the same two-phone, one-after-the-other flow.
- Split the explanation into Editing, Upload, Download and Failures and retries sections. Each section states the rules (100-change upload batches, 500-entry download pages, collapsing of queued edits and the base version kept, frozen sent changes) and what happens on each failure, which the original notes only named.
- Stated that the server checks processed change IDs before doing anything else, and that conflicts also record their change ID, so a retried conflicting upload returns the same result.
- Stated that the cursor is saved in the same local transaction as the applied entries, which is how an interrupted download avoids skipping or missing changes. The brief requires this result, but the original did not explain the mechanism.
- Kept the Mermaid sequenceDiagram and the short-notes format, and kept the scope limits (deletes, attachments, sharing, auth) at the end.
- Added a short summary at the top so a reader gets the whole flow in four bullets before the details.
- Expanded each term into a plain definition and added Outbox and Conflict note, which the original used without defining.
- Explained why the change ID matters: it lets the server recognize a retried change.
- Explained why an edit's outbox entry keeps the first edit's base version, since that is what the server compares against.
- Renamed 'Phone' and 'Server' state descriptions to say where the cursor is stored and what each table is for.
- Spelled out that the cursor and the page's entries are updated in one local transaction, and why that matters.
- Clarified that creating a conflict note also adds a change log entry, which is why every phone receives it.
- Added a sentence before the diagram explaining the scenario, so the diagram reads on its own.
- Kept the Mermaid diagram, its participants, and its message order unchanged, since the diagram is the requested output.
- Defined 'SQLite', 'diff', and 'change log' in plain words at first use, so a reader outside the project can follow them.
- Changed 'Each sync uploads first, then downloads' to an explicit 'upload first, then download, always in this order' with a short statement of when a sync starts.
- Added a 'Reading the diagram' list after the sequence diagram explaining the accepted and conflict outcomes and what Phone B's local copy of N becomes after its download.
- Split the server's upload handling into three numbered cases (already seen, accepted, conflict) so the logic reads in order.
- Stated the cursor and the local database write in the 'Where state lives' section in terms of why they are stored together (updated together), without changing the design.
- Replaced the terse 'Failures and retries' bullets' wording with the same meaning written in full sentences, and made each failure case name the situation first.
- Kept the Mermaid diagram, the section order, and all design rules unchanged.

### Holes
- None.
