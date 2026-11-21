Sync design notes (notes app)

Failure first, since that's the tricky part. If the upload drops, the pending queue is kept and resent with the same change IDs. The backend looks each ID up in its processed-ID table and hands back the saved result, so it's never applied twice; for a conflict it also sends the record's current text and version fresh. Things leave the unsynced list only once the sync API answers accepted or conflict, and accepted ones also get their local version bumped. On the download side, the checkpoint only moves inside the same local transaction that applies a page, so if a download breaks halfway, the page that didn't commit gets fetched again from the last saved high-water mark and nothing already committed is lost. If the server is down or errors, the round is abandoned without touching local state and retried at the next trigger. Storage: the store on the backend has the notes with current body and version, the change log (seq, note, version, body) and the processed-change-ID table. Each handset has, all in SQLite, its notes with the version they're based on, its outbox (UUID, note, base version, full body, sent flag), and the cursor. Once an entry has gone out over the wire it's frozen and never touched again. Anything typed into that note afterwards becomes a second entry parked without a base until the first is answered; then it inherits the new version if the first was accepted, or the first one's old base if it conflicted (so it ends up as a copy too), and it rides along on the next upload.

```mermaid
sequenceDiagram
    participant PA as phoneA
    participant API as backend
    participant DB as store
    participant PB as Device 2
    Note over PA,PB: N starts at v7 everywhere, checkpoints at 500
    PB->>PB: edit N base v7 into unsynced list as c2
    PA->>PA: write N locally, UI updates, pending queue gets c1 base 7
    Note right of PA: more edits to N while c1 hasn't gone out just replace c1 body, base stays 7
    PA->>API: sync - upload c1 with full body and base 7, max 100 per batch
    Note right of PA: c1 flagged sent here, locked from now on
    API->>DB: c1 seen before?
    DB-->>API: no
    Note left of DB: if it had been seen the saved result is returned and nothing is written
    API->>DB: v7 matches so N becomes v8, seq 501, c1 stored as accepted, all one transaction
    API-->>PA: ok v8
    PA->>PA: drop c1 from outbox, N version 8, parked follow-up for N if any gets base 8
    PA->>API: download since 500
    API->>DB: read
    DB-->>API: rows
    API-->>PA: 501 N v8, done
    PA->>PA: apply plus checkpoint 501 together
    Note over PA,DB: download is paged 500 per page, oldest first, keep asking until the backend says no more
    PB->>API: upload c2 base 7
    API->>DB: c2 new, current is v8 so mismatch
    API->>DB: conflict copy N2 titled original title plus (conflict) with c2 body, seq 502, c2 stored as conflict N2, one transaction
    API-->>PB: conflict, N2, plus N v8 text
    PB->>PB: remove c2 from pending, write v8 text into N
    PB->>API: get changes after 500
    API-->>PB: 501 and 502
    PB->>PB: N2 added, N already v8 i.e. phoneA text, cursor 502
    Note over PB: the backend never merges text, first arrival wins, loser lives on in N2
    Note over PA: phoneA picks up N2 next time
    Note over PA,PB: syncs fire on reconnect, foreground, every 60s while online, push then pull, one at a time per device
```

Also, edits are local first with no network wait. One more race: if something comes down for a note that still has an unanswered change, the local copy is left alone but the checkpoint still moves on past it. The next upload then conflicts, gets turned into a copy on the server side, and the reply's current text and version are written into the note (unless a parked follow-up still needs the local text, in which case its own conflict reply does that).
