## Review of sync-01 (self-review, author sonnet, seeded-implicit)

Rounds: 3. Ended: passes.

### What changed
- Replaced the vague bullets with concrete rules for queuing, upload, conflicts, download and cursor handling, since the original could not be understood without project knowledge
- Added a 'Where state lives' section naming each table on the phone and server and what its fields hold, and defined the change_id, base_version, cursor and processed_changes terms on first use
- Rewrote the diagram with concrete versions and sequence numbers, with note boxes at each step that say what the server does, and added a lost-response retry for Phone A
- Showed the conflict copy being created, the resulting log entry, and both phones picking it up on download, which the original diagram skipped
- Added a 'Failure and retry' section covering lost responses, server crashes, interrupted downloads and app kills
- Stated the open edge cases explicitly: edits to a frozen in-flight change, and a pending local change when a download arrives
- Included the batch limits (100 per upload, 500 per download page) in the rules
- Kept the Mermaid sequenceDiagram format with notes before and after it
- Added a short glossary (change, write, base_version) so terms are defined before use
- Spelled out cursor as the highest server log seq applied
- Broke dense paragraphs (queuing, sync triggers, download) into bullets and numbered steps
- Stated what happens to a later queued change if the earlier one ends in conflict (keeps its base_version and will conflict too)
- Clarified in Download that a pending local change means the body is not overwritten
- Explained the lost-response arrow (--x) and that A's retry happens within the same sync
- Reworded the failure bullets into short step-by-step form; no change to the design
- Added a definition that a note's body includes its title, since the server needs the title to name conflict copies.
- Added a first Queuing bullet stating that every edit is saved locally at once and then queued, matching the brief.
- Split the later-edit rule into an explicit two-case list (accepted vs conflict) for easier reading.
- Reworded Upload and Download rules slightly for directness (e.g. 'for that change', 'applies a page').
- Clarified the diagram intro: the crossed arrow shows the lost response and A retries within the same sync.
- Removed trailing periods and bold label punctuation inconsistencies; made Failure section bullets consistently nested.
- Diagram left unchanged.

### Holes
- None.
