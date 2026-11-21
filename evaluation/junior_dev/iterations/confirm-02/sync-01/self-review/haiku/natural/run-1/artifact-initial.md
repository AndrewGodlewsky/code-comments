# Sync flow for the offline-first notes app

Status: design only, no code yet.

## Summary

Phones write every edit to their local database first and queue it for upload. The server is the single source of truth. It decides conflicts by comparing each change's starting version with the note's current version, and it never merges text. Every accepted write bumps the note version and appends to a change log with an increasing sequence number. A sync uploads the queue, then downloads the log from the phone's saved cursor. Every step can be repeated safely.

## Where state lives

| Place | What it stores | Notes |
|---|---|---|
| Phone, notes table | Title and displayed body | Shows the user's latest edit at once, including unsent edits |
| Phone, pending queue | Change id, note id, base version, full body, state (queued or in flight) | One row per queued change. Written in the same local transaction as the note edit |
| Phone, sync state | Download cursor (last applied log seq) | Moves only in the same transaction that applies a download page |
| Server, notes | Id, title, body, version | Version changes only inside a write transaction |
| Server, change log | Seq, note id, version, title, body | Append-only. Seq is the download cursor |
| Server, applied changes | Change id (per user), result, seq, conflict note id | Idempotency record. A repeated change id gets the stored result back |

## Sequence diagram

```mermaid
sequenceDiagram
    autonumber
    participant A as Phone A
    participant B as Phone B
    participant API as Server API
    participant DB as Server DB and change log

    Note over DB: Note N is at version 3. Last log seq is 100
    Note over A,B: Both phones hold N at version 3 with download cursor 100, offline

    rect rgb(240,240,240)
    Note over A: Offline. Edit 1 to N is saved locally and queued
    Note over A: Queue row c-A1, note N, base 3, body A1
    Note over A: Edit 2 to N collapses into c-A1, body A2, base stays 3
    Note over B: Offline. Edit to N is saved locally and queued
    Note over B: Queue row c-B1, note N, base 3, body B1
    end

    Note over A: Connection returns. Sync takes the sync lock
    A->>API: POST upload batch with c-A1 (note N, base 3, body A2)
    API->>DB: Begin transaction. Check c-A1 is new and N version equals 3
    DB-->>API: Commit. N becomes version 4, log seq 101 appended, c-A1 recorded as accepted
    API-->>A: c-A1 accepted, N version 4, seq 101
    Note over A: Remove c-A1 from queue
    A->>API: GET changes after cursor 100, limit 500
    API-->>A: Page with seq 101 (N version 4, body A2), hasMore false
    Note over A: Apply page in one local transaction. Cursor becomes 101

    Note over B: Connection returns. Sync takes the sync lock
    B->>API: POST upload batch with c-B1 (note N, base 3, body B1)
    API->>DB: Begin transaction. Check c-B1 is new. N version 4 does not equal base 3
    DB-->>API: Commit. New note N2 with title plus (conflict) and body B1, version 1, log seq 102 appended, c-B1 recorded as conflict
    API-->>B: c-B1 conflict, current version 4, conflict note N2
    Note over B: Remove c-B1 from queue. Body B1 now lives on the server as N2
    B->>API: GET changes after cursor 100, limit 500
    API-->>B: Page with seq 101 (N version 4, body A2) and seq 102 (N2 version 1, body B1)
    Note over B: Apply page in one local transaction. Cursor becomes 102
    A->>API: Next sync, GET changes after cursor 101
    API-->>A: Page with seq 102 (N2 version 1). Phone A now also has the conflict note
```

## Notes on the diagram

1. Both phones start at version 3. Phone A edits twice while offline. The second edit collapses into the queued change c-A1, which keeps base version 3.
2. Phone A syncs first. Its base matches the server, so the server accepts it, writes version 4, appends seq 101 and records the result. All three happen in one transaction.
3. Phone B syncs second. Its base 3 no longer matches version 4, so the server rejects c-B1 as a conflict. It saves B1 as a new note N2 and logs it as seq 102. Note N is not changed.
4. The losing body is never deleted. It stays on the server as N2, and every phone picks it up on its next download.
5. Phone B removes c-B1 only after it has stored the conflict result. Its local N then shows the winner once seq 101 is applied.
6. The base version lives in the queue row, not in the note row. A download can move the note forward without changing what the pending change was based on.

## Failure and retry

| Failure | What happens | Why nothing is applied twice or skipped |
|---|---|---|
| Connection drops before the upload reaches the server | Nothing is committed. The change stays queued | Retry sends the same change id and base |
| Connection drops after the server commits but before the phone gets the response | The phone does not know the result | Retry sends the same change id. The server returns the stored result and writes nothing |
| Drop partway through a batch of up to 100 changes | Changes already committed stay committed. The rest do not run | Each change commits on its own. Retry resends the batch, and committed changes return their stored results |
| Drop during a download page | The phone transaction does not commit and the cursor does not move | Retry starts from the old cursor. Entries carry full bodies and versions, so replaying a page gives the same result |
| App is killed between applying a page and saving the cursor | Cannot happen | Page and cursor are saved in one local transaction |
| Server crashes mid-write | The database rolls back the whole transaction | Nothing is half-applied, so retry is a normal first attempt |
| A sync trigger fires while a sync is running | The second trigger does not start another sync | A per-phone sync lock lets only one upload-then-download cycle run at a time |
| User edits a note whose change is already in flight | The edit goes into a new queue row for that note and waits | Only one change per note is in flight. If the earlier change is accepted, the waiting row's base becomes the accepted version. If it conflicts, the waiting row keeps its old base and the server judges it |
| Phone is offline for hours | Changes stay queued | The change id stays the same, so a late retry is still safe, as long as the server still has the applied-changes record (see open questions) |

Other rules:

- Every server write for a change, including the note update or conflict note, the log append and the applied-changes record, commits together or not at all.
- Writes are serialized per account, so seq order matches commit order. Without this, a download could see seq 102 committed while 101 is still open and move the cursor past 101 for good.
- A download applies an entry only when its version is higher than the phone's stored server version for that note. Replaying an older entry does nothing.
- If a note has a queue row, a download updates only the stored server version. The displayed body keeps the user's unsent edit.
- A change id is created once, when its queue row is first written, and kept when later edits collapse into that row.
- A sync loops over the upload batches until the queue is empty, then loops over download pages until the server reports no more.

## Open questions

1. Retention of the applied-changes record. A phone offline for longer than the retention window could retry a change the server has forgotten, and that change would be applied twice. Keep records at least as long as the longest allowed offline period, or until the phone confirms it has the result.
2. Edits made after a conflict. A later edit sent with its old base will become a second conflict copy. The alternative is to rebase it onto the winner and show the user both versions. That goes against the no-merge rule, so it needs a product decision.
3. Throughput of serialized writes per account. This is fine for one person's notes across a few phones. It needs a check if many devices write to the same account at once.