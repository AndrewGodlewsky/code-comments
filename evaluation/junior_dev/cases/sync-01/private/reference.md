## Notes sync: sequence

**Where state lives**
- **Phone (local SQLite):** `notes` (title, body, `version` = the server version this copy is based on); `outbox` of pending changes (`change_id` UUID, `note_id`, `base_version`, full body, `sent` flag); `cursor` = the highest change-log sequence number applied.
- **Server DB:** `notes` (current body and version); `change_log` (seq, note_id, version, body); `processed_changes` (change_id → result).

**Outbox rules**
- An edit writes `notes` and the outbox in one local transaction, and the UI updates at once.
- While a note's change has not been sent, further edits replace its body. Its `change_id` and `base_version` stay the same.
- Once a change has been sent it is **frozen**: its body and `change_id` never change. A later edit to that note goes into a **new change that is held** until the sent one is confirmed. If the sent one was accepted, the held change takes the confirmed new version as its base. If it was a conflict, the held change keeps the old base, so it also becomes a conflict copy. Either way it goes out in the next push.
- A change leaves the outbox only when the server confirms it (accepted or conflict).

**When a sync runs:** on reconnect, when the app comes to the foreground, and every 60 s while online. A phone runs one sync at a time, and each sync is a **push, then a pull**.

```mermaid
sequenceDiagram
    autonumber
    actor U as User
    participant A as Phone A local DB and outbox
    participant B as Phone B local DB and outbox
    participant S as Sync server
    participant D as Server DB

    Note over A,B: Both phones offline. Note N is at server version 7 on both. Both cursors are 500.
    U->>A: Edit note N
    A->>A: Save body locally, UI updates, add outbox change c1 for N with base 7
    Note over A: c1 not sent yet, so another offline edit to N replaces c1 body and keeps base 7
    U->>B: Edit note N
    B->>B: Save body locally, add outbox change c2 for N with base 7

    Note over A,S: Phone A reconnects first. Sync step 1 is PUSH.
    A->>A: Mark c1 sent. From now on c1 is frozen
    A->>S: Push batch of up to 100 changes, here c1 with base 7 and full body
    S->>D: Look up c1 in processed_changes
    alt c1 already processed, this is a retry
        D-->>S: Stored result for c1
    else c1 is new and base 7 equals current version 7
        S->>D: One transaction - N becomes v8, append log seq 501, store c1 as accepted v8
    end
    S-->>A: c1 accepted, N is now v8
    A->>A: Remove c1 from outbox, set local N version to 8
    Note over A: An edit to N made while c1 was in flight would sit in a held change, now given base 8 for the next push

    Note over A,S: Sync step 2 is PULL
    loop until server reports no more pages
        A->>S: Pull log entries after cursor 500
        S->>D: Read entries after seq 500, oldest first, at most 500
        S-->>A: Entry 501 for N v8, no more pages
        A->>A: One transaction - apply entries and save cursor 501
    end

    Note over B,S: Phone B reconnects later. PUSH.
    B->>S: Push c2 with base 7 and full body
    S->>D: c2 is new, but base 7 differs from current version 8, so conflict
    S->>D: One transaction - create note N2 titled with N title plus (conflict) holding c2 body, log seq 502, store c2 as conflict N2
    S-->>B: c2 conflict, body saved as N2, current N is v8 with its body
    B->>B: One transaction - remove c2 from outbox, overwrite N with the v8 body

    Note over B,S: PULL
    B->>S: Pull log entries after cursor 500
    S-->>B: Entries 501 for N v8 and 502 for N2 v1, no more pages
    B->>B: One transaction - N already at v8, add N2, save cursor 502
    Note over B: N shows Phone A text. N2 shows Phone B text. Nothing lost.
    Note over A: Phone A gets N2 on its next pull
```

**Failure and retry**
- **Push drops before the response arrives:** the changes stay in the outbox, because a change leaves only when the server confirms it. The next sync resends them unchanged, with the same `change_id`s (sent changes are frozen). The server finds them in `processed_changes` and returns the stored result, so nothing is applied twice. For a conflict it also returns the note's current body and version, read fresh.
- **Pull drops partway through:** the cursor is saved in the same local transaction as the page it covers. A page that did not commit is rolled back and fetched again from the last saved cursor on the next sync, and a committed page is never lost.
- **Server unreachable or erroring:** the sync stops and nothing local changes. The next trigger tries again.
- **Pulled entry for a note that still has an unconfirmed outbox change** (for example, edited during the sync): the phone leaves that note's local body alone, but the cursor still moves past the entry. When the change is pushed it conflicts. The server saves the local body as a conflict copy, and the conflict response carries the note's current body and version, which the phone writes into the note. If a held change for that note is still waiting, the phone keeps the local body for it, and that change's own conflict response brings the server body. Either way the phone ends with the winning version plus the copy.
- The server never merges text. The first write to arrive wins.
