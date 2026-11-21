# Live cursors and presence: design

## Summary

- **No new infrastructure.** Redis holds all presence and cursor state, and the pub/sub channel `pres:{docId}` carries the live changes. The edit path, the load balancer and the document service are unchanged, and nothing here touches Postgres.
- **Postgres presence goes away.** The presence table, the 30 s client polling and the nightly cleanup job are retired.
- **Entries expire.** Every Redis entry has an expiry that live nodes refresh. When a node dies, its entries stop being refreshed and any surviving node removes them.
- **One counter orders everything.** Each document has one counter, `_n`, in the `cur:{docId}` hash. Each event gets the next number as `v`, inside the same Lua script that publishes it. Receivers use `v` to discard stale or duplicate messages.

## Where state lives

| State | Location | Created by | Refreshed by | Removed by |
|---|---|---|---|---|
| Socket, `connId`, `userId`, `minV` (the snapshot's `n`), `lastCursorAt` | Node memory (`localSockets`) | WebSocket connect | None | Socket close, or node death |
| Pub/sub subscription `pres:{docId}` | Node, per document | First local socket on the document | None | Last local socket closes, or node death |
| `pres:{docId}`, a ZSET with member `userId\|connId` and score = expiry in ms | Redis primary | `join` script | `touch` script every **10 s** (new score = Redis `TIME` + **30 s**) | `leave` script, `reap` script, or key TTL |
| `cur:{docId}`, a HASH with `_n`, `c:<userId>` = `{rev,pos,v}` and `p:<userId>` = profile | Redis primary | `join` (profile) and `cursor` scripts | Key `EXPIRE 120` on every script call | `leave` or `reap` (when the user's last entry goes), or key TTL |
| Presence list, `lastV[user]`, held cursor, drawn caret `(pos, atRev)`, `appliedRev` | Client memory | `presence_snapshot` and live events | Live events | Reconnect (rebuilt from a new snapshot) |
| Anything about presence or cursors | Postgres | Never | N/A | N/A |

Timings:

| Item | Value |
|---|---|
| Heartbeat | 10 s |
| Entry expiry | 30 s |
| Sweep | every 5 s, by every node that has a local socket on the document |
| Key TTL (backstop) | 120 s |
| Existing WebSocket ping/pong | unchanged (10 s / 20 s) |

- **Scripts use Redis `TIME`.** Entry scores come from Redis `TIME` inside the Lua scripts, so node clock skew does not matter.
- **One Redis, one slot.** Every script runs on the primary, which is a single Redis. Reads never go to the replica, because a stale snapshot would break the `v` ordering. If Redis is ever clustered, the keys need a `{docId}` hash tag.

## Rules

**Server (node)**
- On join, subscribe to `pres:{docId}` first, then run `join`. The script returns a snapshot and its `n`. The node sends the snapshot to the client and sets `conn.minV = n`. After that it forwards only events with `v > minV`, so the join event the node sees from its own publish is not echoed back as a duplicate.
- A cursor message is accepted only if at least 50 ms have passed since the last accepted one on that connection (monotonic clock). Otherwise it is dropped silently. Accepted messages go to the `cursor` script.
- A node never sends a user's own cursor back to that user.

**Server (Lua scripts, each atomic)**
- `join` first reaps expired entries, then does `ZADD`. The profile is stored only if this is the user's first live entry, and only then does it publish `join`. A second tab of the same user publishes nothing. It always returns a snapshot of the live users, their cursors and `n`.
- `touch` is `join` without the snapshot. If Redis lost an entry (failover or a stalled node), it is re-added and the join is announced if the user had vanished.
- `cursor` does nothing if `userId|connId` is not in `pres`. Otherwise it increments `_n`, stores `c:<user>` and publishes `cursor {userId, rev, pos, v}`.
- `leave` and `reap` remove the entries. If the user has no entry left, they delete `c:<user>` and `p:<user>`, and publish `leave {userId, v}`.

**Client**
- **Presence.** Apply an event only if `v > snapshot.n`. A reconnect replaces the whole list and clears `lastV` and held cursors.
- **Backwards jumps.** For each user, keep `lastV[user]`. Drop any cursor with `v <= lastV[user]`, whatever order it arrives in. This is checked on arrival, before the revision check. Only the newest cursor per user is kept, held or drawn.
- **Future revisions.** If `cursor.rev > appliedRev`, hold the cursor and draw nothing. After each applied remote op, draw any held cursor whose `rev <= appliedRev`.
- **Older revisions.** If `cursor.rev < appliedRev`, draw at `transformPosition(pos, rev, appliedRev)`. If it throws `HistoryGone`, drop the position and hide that caret until the next update.
- **Keeping drawn carets current.** Re-transform each drawn caret from its `atRev` on every applied op, so it never falls outside the 500-revision history.
- **Sending.** Send `{t:"cursor", docId, rev: appliedRev, pos}` at most once per 60 ms. The margin over 50 ms covers network bunching. There is always a trailing send, so the final position goes out. One extra re-send happens 1 s after the last move. This repairs a final update the server dropped, which would otherwise leave an idle caret stale.

## Choices and limits

- **One caret per user.** Two tabs of the same user share one caret: the tab that moved last. If that tab closes while the other stays open, the caret stays at its last position until the other tab moves.
- **Display data.** Profile data (name and avatar) is taken from the session at join and kept in `p:<userId>`. The caret colour is derived from `userId`.
- **Join check.** The "does this user have another entry" check scans the document's `pres` set. That is cheap, because a document has tens of connections.
- **Cursor writes.** The worst case is about 20 Redis writes per second per active user. This is the price of showing idle users' carets on join. Pub/sub alone stores nothing, so it cannot do that.
- **Redis outage.** Editing is unaffected, because the edit path does not use these scripts. Presence and cursors freeze and are rebuilt by the next `touch` or `join` after recovery.

## Sequence

```mermaid
sequenceDiagram
    participant A as Alice tab 1
    participant A2 as Alice tab 2
    participant N1 as Node N1
    participant R as Redis primary
    participant N2 as Node N2
    participant B as Bob
    participant DS as Document service

    Note over B,N2: Before: Bob is on N2 and subscribed to pres:doc and ops:doc
    Note over R: pres:doc = {bob|c9 expires T+30s}<br/>cur:doc = {_n=40, c:bob={rev 118, pos 52, v 37}, p:bob}

    rect rgb(235, 245, 255)
    Note over A,DS: 1. Alice joins on a different node
    A->>N1: WebSocket connect and open(doc), applied rev 117
    N1->>N1: connId c1, add to localSockets
    N1->>R: SUBSCRIBE pres:doc (first local socket)
    N1->>R: EVALSHA join(doc, alice, c1, profile)
    Note over R: atomic: reap expired, ZADD alice|c1 with score TIME+30s,<br/>EXPIRE 120, Alice is new so HSET p:alice, n=41 and PUBLISH join v=41
    R-->>N1: snapshot n=41, users bob and alice, cursors {bob: rev 118, pos 52, v 37}
    R--)N2: pres:doc join alice v=41
    R--)N1: pres:doc join alice v=41, dropped because v is not above minV 41
    N1-->>A: presence_snapshot (includes Bob's idle caret)
    N2-->>B: presence_join alice, avatar appears
    Note over A: Bob's caret has rev 118 and Alice has applied 117, so it is HELD, not drawn
    DS--)R: PUBLISH ops:doc rev 118
    R--)N1: ops:doc rev 118
    N1-->>A: remote_op 118
    Note over A: appliedRev=118, held cursor is now drawable, caret drawn at pos 52
    end

    rect rgb(240, 255, 240)
    Note over A,DS: 2. Cursor move, older revision, and ordering
    DS--)R: PUBLISH ops:doc rev 119
    R--)N2: ops:doc rev 119
    N2-->>B: remote_op 119 (Bob applies 119, Alice has not yet)
    A->>N1: cursor(rev 118, pos 7)
    Note over N1: per-connection check: under 50 ms since last accepted means silent drop.<br/>Here it passes, never reaches the document service or Postgres
    N1->>R: EVALSHA cursor(doc, alice, c1, 118, 7)
    Note over R: alice|c1 is live, n=42, HSET c:alice, PUBLISH cursor v=42
    R--)N2: pres:doc cursor alice rev 118, pos 7, v=42
    N2-->>B: cursor alice (rev 118, pos 7, v=42)
    Note over B: lastV[alice]=42. appliedRev is 119, so draw at transformPosition(7, 118, 119).<br/>If it throws HistoryGone, hide the caret.<br/>A late cursor with v=41 arriving now is dropped, so no backwards jump
    R--)N1: pres:doc cursor alice v=42, not sent back to Alice
    end

    rect rgb(255, 250, 230)
    Note over A,DS: 3. Heartbeat and sweep, in the background
    loop every 10 s, per node and document
        N1->>R: EVALSHA touch(doc, alice, [c1, c2]) sets score TIME+30s, EXPIRE 120
        N2->>R: EVALSHA touch(doc, bob, [c9]) sets score TIME+30s, EXPIRE 120
    end
    loop every 5 s, per node with a local socket on the doc
        N2->>R: EVALSHA reap(doc) removes entries with score below TIME
        Note over R: normally removes nothing
    end
    end

    rect rgb(245, 240, 255)
    Note over A,DS: 4. Two tabs, then a clean leave
    A2->>N1: WebSocket connect and open(doc)
    N1->>R: EVALSHA join(doc, alice, c2, profile)
    Note over R: Alice already present, so no publish. Presence list is unchanged for Bob
    R-->>N1: snapshot
    A2->>N1: tab closes
    N1->>R: EVALSHA leave(doc, alice, c2)
    Note over R: ZREM alice|c2, alice|c1 remains, so no event
    A->>N1: tab closes (clean close)
    N1->>R: EVALSHA leave(doc, alice, c1)
    Note over R: ZREM, Alice has no entry left, HDEL c:alice and p:alice,<br/>n=43, PUBLISH leave v=43
    N1->>R: UNSUBSCRIBE pres:doc (no local sockets left)
    R--)N2: pres:doc leave alice v=43
    N2-->>B: presence_leave alice, avatar and caret removed (well under 2 s)
    end

    rect rgb(255, 240, 240)
    Note over A,DS: 5. Node crash
    Note over A,N1: Alice reopens the doc on N1, same join as step 1.<br/>Entry alice|c3 has score T+30s, last touch at time T
    N1--xR: N1 is killed. No cleanup, no leave, sockets just drop
    Note over R: alice|c3 is no longer refreshed.<br/>Subscription and conn state vanish with the node
    Note over N2,R: while T+30s has not passed, Alice is still listed. This window is bounded
    N2->>R: EVALSHA reap(doc) at the first sweep after T+30s
    Note over R: alice|c3 is below TIME and is removed. Alice has no other entry,<br/>so HDEL c:alice and p:alice, n=44, PUBLISH leave v=44
    R--)N2: pres:doc leave alice v=44
    N2-->>B: presence_leave alice, gone at most 35 s after the last heartbeat (limit 45 s)
    Note over R: If every node on the doc died, no one sweeps, but<br/>pres:doc and cur:doc hit their 120 s key TTL and are deleted
    end
```

Notes on step 5:
- If Alice's browser reconnects to another node before expiry, her new entry has a new `connId`. The old entry expires silently, because she still has a live entry and no leave is published.
- A user whose connection is closed by the existing 20 s pong timeout goes through the same `leave` path as a clean close.
