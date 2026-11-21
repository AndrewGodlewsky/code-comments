# Notes sync: sequence design

## Where state lives

**On each phone (SQLite)**

- `notes(id, title, body, server_version)` holds what the UI shows. `server_version` is the last server version this phone knows for the note. Note ids are UUIDs made on the phone, so a note can be created offline.
- `outbox(change_id, note_id, base_version, title, body, state)` has one row per queued change. `change_id` is a UUID made when the row is created. `state` is `pending` or `in_flight`.
  - If the user edits a note that has a `pending` row, the edit goes into that same row: title and body are replaced, and `change_id` and `base_version` stay as they were.
  - An `in_flight` row is frozen. It may already have been applied on the server, so nothing is ever collapsed into it (see "Edit during upload" below).
  - The edit to `notes` and the edit to `outbox` are written in one local transaction, so the UI and the queue always agree.
- `sync_state(last_seq)` is the download cursor: the highest log sequence number this phone has fully applied.

**On the server (one database)**

- `notes(id, title, body, version)` is the source of truth.
- `change_log(seq, note_id, version, title, body)` gets one row per accepted write, including the creation of conflict copies. `seq` comes from a single counter row that is updated inside the write transaction. That makes seqs commit in order with no gaps, so a reader can't see seq 42 while seq 41 is still uncommitted and then step past it.
- `applied_changes(change_id, result)` stores either `accepted(version)` or `conflict(conflict_note_id)`. This table is what makes uploads idempotent.

**Server rule for one uploaded change** (each change is one transaction: the version check, the note write, the log append and the `applied_changes` row are all saved or none are):

1. If `change_id` is already in `applied_changes`, apply nothing. Return the stored result.
2. Otherwise, if `base_version` equals the note's current version (or `base_version` is 0 and the note doesn't exist yet, which is a create), write the note at version + 1, append to the log and record `accepted`.
3. Otherwise it is a conflict. Leave the note as it is. Create a new note with a new id, the title plus " (conflict)", the uploaded body and version 1. Log it and record `conflict`. The response includes the winning note's current state and the conflict copy, so the phone can update right away without waiting for its download.

Title and body together count as the note's content here. The brief says "full note body", and I've assumed the title travels with it.

## Sequence: two phones edit the same note offline, then sync one after the other

```mermaid
sequenceDiagram
    participant A as Phone A (SQLite)
    participant S as Sync server
    participant B as Phone B (SQLite)

    Note over A,B: Start. Note n1 Groceries is at version 7 on the server and on both phones.<br/>Both phones have last_seq = 40.

    Note over A,B: Both phones offline
    A->>A: Edit n1. Save to notes, add outbox row cA (base 7, body A1)
    A->>A: Edit n1 again. Collapse into cA (base still 7, body A2)
    B->>B: Edit n1. Save to notes, add outbox row cB (base 7, body B1)

    Note over A: Connection back. Sync starts, upload first
    A->>A: Mark cA in_flight
    A->>S: POST /upload [cA n1 base 7 body A2]
    S->>S: One transaction. n1 is at 7, matches base. Write v8, log seq 41, record cA accepted v8
    S--xA: 200 [cA accepted v8] (connection drops, response lost)
    Note over A: No reply. cA stays in_flight and is resent unchanged
    A->>S: POST /upload [cA n1 base 7 body A2] (retry, same change_id)
    S->>S: cA is already in applied_changes. Apply nothing
    S-->>A: 200 [cA accepted v8] (stored result)
    A->>A: One transaction. n1 server_version 8, delete outbox row cA
    A->>S: GET /changes after=40 limit=500
    S-->>A: [seq 41 n1 v8], has_more false
    A->>A: One transaction. n1 already at v8 so skip, last_seq 41

    Note over B: Later. Connection back on Phone B
    B->>B: Mark cB in_flight
    B->>S: POST /upload [cB n1 base 7 body B1]
    S->>S: One transaction. n1 is at 8, base is 7, so conflict.<br/>Create n2 Groceries (conflict) body B1 v1, log seq 42, record cB conflict n2. n1 untouched
    S-->>B: 200 [cB conflict, winner n1 v8 body A2, copy n2 v1 body B1]
    B->>B: One transaction. n1 now shows A2 at v8, insert n2 at v1, delete outbox row cB
    B->>S: GET /changes after=40 limit=500
    S--xB: [seq 41, seq 42] (connection drops mid-page)
    Note over B: Page transaction rolled back, last_seq still 40
    B->>S: GET /changes after=40 limit=500 (retry)
    S-->>B: [seq 41 n1 v8, seq 42 n2 v1], has_more false
    B->>B: One transaction. Both already applied so skip, last_seq 42

    Note over A: Next 60-second tick
    A->>A: Outbox empty, nothing to upload
    A->>S: GET /changes after=41 limit=500
    S-->>A: [seq 42 n2 v1], has_more false
    A->>A: One transaction. Insert n2 Groceries (conflict), last_seq 42

    Note over A,B: End. Both phones show n1 = A2 (v8) and n2 = B1 (v1). No edit was lost.
```

## Failure and retry

- **Upload request lost before it reaches the server.** Nothing was applied. The row is still `in_flight` and is resent with the same `change_id` on the next sync.
- **Server applied the change but the response was lost** (shown above). The retry carries the same `change_id`. The server returns the stored result and doesn't write a second time.
- **Batch cut off partway.** Each change in a batch is its own server transaction, so some may be applied and others not. The phone resends the whole batch. Applied changes come back as stored results and the rest are applied normally. The response gives one result per `change_id`.
- **App killed mid-upload.** `in_flight` rows survive in SQLite. On the next launch they are resent exactly as they are, never edited. Because any `in_flight` row might already be applied, it can't be collapsed into.
- **Edit during upload.** An edit to a note whose row is `in_flight` creates a second `pending` row that waits behind it and is not sent until the first row has a result. If the first is `accepted(v)`, the waiting row's base becomes `v`. If the first is a `conflict`, the user's newer text belongs with their own copy, so the waiting row is moved to the conflict note with base 1. Locally, that note shows the newer text. Nothing overwrites the winner, so "first write wins" still holds.
- **Download interrupted** (shown above). Applying a page and moving `last_seq` forward happen in one SQLite transaction. A page that was lost or only half applied is rolled back, and the phone fetches again from the same cursor. Applying an entry is idempotent because it only writes when the entry's version is higher than the local `server_version`. Gap-free, in-order seqs on the server mean the cursor can't skip an entry.
- **Download entry for a note that still has an outbox row.** The local body isn't overwritten, because it holds the user's unsent text. The cursor still advances. That note's upload settles it: it will conflict, and the conflict response carries the winner.
- **More than 100 queued changes or more than 500 log entries.** Upload loops in batches of up to 100 until the outbox is empty. Download loops page by page while `has_more` is true.
- **Overlapping triggers** (reconnect, foreground and the timer firing close together). Only one sync runs at a time on a phone. A trigger that arrives during a sync sets a "run again" flag, and a single extra sync runs when the current one finishes.

## Open points to decide

- **How long to keep `applied_changes`.** Retries are only safe while the record exists. The simplest choice is to keep it forever, since it is one small row per write. If it is ever pruned, a phone that sends a retry after the record is gone could get that change applied twice.
- **First sync of today's local-only notes.** Each existing note is queued as a create (`base_version` 0) the first time the phone signs in. A second phone that signs in has its own notes uploaded the same way and then downloads everything from seq 0.
