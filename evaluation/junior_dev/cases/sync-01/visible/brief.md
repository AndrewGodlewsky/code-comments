## Sync for the offline-first notes app

We're adding multi-device sync to our notes app. A user can have several phones signed in, and must be able to read and edit notes with no network at all. Please design the sync flow before anyone writes code.

**Fixed requirements**

- Every edit is saved to the phone's local database straight away and shows up in the UI with no network round trip. The phone then queues the edit for upload.
- A queued change carries the full note body (no diffs) plus the server version the edit started from. If the user edits the same note several times before it uploads, those edits collapse into one queued change. That change keeps the original starting version.
- The server is the source of truth. Each note has an integer version that goes up by one on every accepted write. Every accepted write is also added to a server change log with an increasing sequence number. Phones catch up by reading that log.
- A sync runs when the phone gets its connection back, when the app comes to the foreground, and every 60 seconds while online. Each sync uploads first, then downloads.
- An upload batch holds at most 100 changes. A download page holds at most 500 log entries.
- The server decides conflicts. An upload is a conflict when its starting version doesn't match the note's current version. We do not merge text. The write that reaches the server first wins. The losing body is never thrown away: the server saves it as a new note, titled with the original title plus " (conflict)", and every device picks that note up on its next download.
- Mobile connections drop at any point. Retrying an upload must never apply the same change twice. An interrupted download must not cause a phone to skip or miss changes.

**Existing system**: today the app is local-only (SQLite on the phone). There is no sync server yet.

**Out of scope**: deletes, attachments, sharing between users, auth.

**What I want**: a Mermaid `sequenceDiagram` with short notes before or after it. The diagram should show two phones that both edit the same note while offline and then sync one after the other. The notes should say where state lives and what happens on failure and retry.
