# Live cursors and presence: design and sequence diagram

## Summary

Nodes keep the truth about their own connections in memory. Redis holds a short-lived copy per document so that a joiner gets a snapshot. Redis pub/sub carries the live changes on a new channel, `pres:{docId}`, next to the existing `ops:{docId}`. Everything is on the existing Redis. Nothing is added, and the edit path, document service, Postgres and load balancer are untouched. The Postgres presence table and its 30 s polling are retired.

## Where state lives

| State | Where | Written by | Refreshed or removed by |
|---|---|---|---|
| Socket, `connId`, `userId`, last cursor time | Node memory (`localSockets`) | Owning node | Gone when the node dies. It is the source Redis is rebuilt from. |
| Liveness of each connection | Redis ZSET `pres:z:{doc}`, member `connId`, score = expiry (Redis `TIME` + 30 s) | Join script | Node heartbeat every 10 s. Removed by clean leave or by the sweep. |
| Who the connection is | Redis HASH `pres:i:{doc}`, `connId` to `userId, name, avatar` | Join script | Same scripts as the ZSET, which always change both together. |
| Last cursor per connection | Redis HASH `pres:c:{doc}`, `connId` to `seq, rev, pos` | Cursor script | Heartbeat re-writes it. Removed together with its ZSET entry. |
| Live changes | Pub/sub `pres:{doc}`: `join`, `cursor`, `conn_left` | The same Lua scripts, atomically with the write | Not stored. |
| Held and shown carets, `lastSeq` per `connId` | Client memory | Client | Dropped on `conn_left`. |

- **Per user, not per tab.** The avatar list is keyed by `userId` and the ZSET by `connId`.
  - `join` is published only when the user had no other live connection.
  - `conn_left` carries `userGone`. It is true only when the user's last connection went.
  - A client removes an avatar only when `userGone` is true.
- **No permanent leftovers.** All three keys have `EXPIRE 90`, refreshed on every join and heartbeat. A document nobody is in therefore empties itself.
- **Redis failover.** Heartbeats upsert with `ZADD` (not `XX`) and re-write the info and cursor. A replica that missed writes is repaired within 10 s.
- **Clock.** Scripts use Redis `TIME`, so nodes' clocks do not matter.
- **Cursors are ephemeral.** They exist only on this path. The document service and Postgres never see them.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant Bob as Bob's tab (new)
    participant NB as Node B
    participant R as Redis (ZSET, HASHes, pub/sub)
    participant NA as Node A
    participant Alice as Alice's tab (already in doc)
    participant NC as Node C
    participant Carol as Carol's tab (already in doc)

    Note over NA,Carol: Alice is on node A and Carol on node C. Both are subscribed to ops:doc1 and pres:doc1 and are in pres:z:doc1.

    rect rgba(120,160,255,0.12)
    Note over Bob,Carol: 1. Bob joins doc1 on node B
    Bob->>NB: WebSocket /ws then Open doc1 (session cookie)
    Note over NB: connId b1, userId bob.<br/>localSockets[doc1] += b1
    NB->>R: SUBSCRIBE ops:doc1 and pres:doc1 (first local socket)
    Note over NB: Subscribe first, then read state.<br/>Duplicates are harmless because every event is idempotent.
    NB->>R: JOIN script (doc1, b1, bob profile)
    Note over R: ZADD pres:z:doc1 (now+30s) b1<br/>HSET pres:i:doc1 b1 (bob, name, avatar)<br/>EXPIRE all three keys 90s.<br/>Reads the snapshot (live users and all cursors).<br/>If bob has no other live connId, PUBLISH join bob.
    R-->>NA: join bob
    NA-->>Alice: presence_join bob (avatar added)
    R-->>NC: join bob
    NC-->>Carol: presence_join bob
    R-->>NB: snapshot (users, cursors incl. idle ones)
    NB-->>Bob: presence_snapshot (full avatar list + carets)
    Note over Bob: Doc loads as today, appliedRev = 90.<br/>Each snapshot cursor goes through the caret rules below.<br/>Idle users show because their cursor is stored, not streamed.
    end

    rect rgba(120,220,160,0.12)
    Note over Bob,Carol: 2. Alice moves her cursor
    Alice->>NA: cursor (doc1, seq 17, rev 88, pos 120)<br/>client sends at most one per 60 ms, trailing edge
    alt arrived less than 50 ms after the last accepted one on this connection
        NA--xAlice: silently dropped, no error, no Redis, no publish
    else accepted
        NA->>R: CURSOR script (a1, seq 17, rev 88, pos 120)
        Note over R: HSET pres:c:doc1 a1 (seq 17, rev 88, pos 120)<br/>PUBLISH pres:doc1 cursor (a1, alice, 17, 88, 120)
        R-->>NB: cursor a1
        NB-->>Bob: cursor (a1, alice, 17, 88, 120)
        R-->>NC: cursor a1
        NC-->>Carol: cursor (a1, alice, 17, 88, 120)
        R-->>NA: cursor a1
        NA-->>Alice: only to her other tabs, never back to a1
    end
    Note over Bob: Caret rules on receipt:<br/>1. seq <= lastSeq[a1]: ignore (out of order or duplicate).<br/>2. Otherwise lastSeq[a1] = seq.<br/>3. rev > appliedRev: hold it, draw after that revision is applied.<br/>4. rev <= appliedRev: pos = transformPosition(pos, rev, appliedRev).<br/>5. HistoryGone: drop the caret until the sender's next update.<br/>Op flow is unchanged: remote_op advances appliedRev, then held carets are released.
    end

    rect rgba(255,200,120,0.14)
    Note over Bob,Carol: 3. Heartbeat (every 10 s per node, nothing goes through the document service)
    loop every 10 s on each node with local sockets on doc1
        NA->>R: REFRESH script (doc1, local connIds, last cursors)
        NB->>R: REFRESH script (doc1, local connIds, last cursors)
        Note over R: ZADD each connId with score now+30s (upsert).<br/>Re-writes info and cursor hashes.<br/>EXPIRE 90s on all three keys.
    end
    Note over NA,NB: A connection that misses the ws ping/pong (20 s) is closed by its node and takes the leave path.<br/>Its score is then no longer refreshed.
    Note over Alice: If appliedRev has moved since her last report she re-sends her cursor<br/>(pos transformed to appliedRev, new seq).<br/>This keeps stored carets inside the 500-revision history for late joiners.
    loop every 5 s on each node with local sockets on doc1
        NB->>R: SWEEP script (doc1)
        Note over R: Removes entries with score below now from the ZSET, info and cursor hashes.<br/>PUBLISH conn_left for each, atomically with the removal.<br/>Usually removes nothing.
        NB->>R: read live users and cursors
        Note over NB: Diffs against what its local clients were sent<br/>and sends corrections. Repairs any missed pub/sub message.
    end
    end

    rect rgba(255,140,140,0.12)
    Note over Bob,Carol: 4. Clean leave: Bob closes his tab (target under 2 s, typically milliseconds)
    Bob->>NB: WebSocket close
    NB->>R: LEAVE script (doc1, b1)
    Note over R: ZREM pres:z:doc1 b1, HDEL pres:i:doc1 b1, HDEL pres:c:doc1 b1
    alt bob has another live connId (second tab)
        R-->>NA: conn_left (b1, bob, userGone false)
        NA-->>Alice: drop b1 caret only, bob stays in the avatar list
    else that was bob's last connection
        R-->>NA: conn_left (b1, bob, userGone true)
        NA-->>Alice: drop b1 caret and bob's avatar
        R-->>NC: conn_left (b1, bob, userGone true)
        NC-->>Carol: drop b1 caret and bob's avatar
    end
    Note over NB: No local sockets left on doc1, so UNSUBSCRIBE ops:doc1 and pres:doc1.
    end

    rect rgba(200,120,255,0.12)
    Note over Bob,Carol: 5. Node A crashes with Alice on it
    Note over NA: Killed with no cleanup.<br/>Alice's sockets drop and pres:z:doc1 still holds a1 with score = last heartbeat + 30s.
    NA--xR: heartbeats stop
    Note over R: a1 stays in Redis until its score passes.<br/>Nothing is published and nothing is yet visible to others.
    loop every 5 s until the score expires
        NC->>R: SWEEP script (doc1)
        Note over R: nothing expired yet
    end
    NC->>R: SWEEP script (doc1)
    Note over R: a1 is expired.<br/>ZREM, HDEL info and cursor.<br/>alice has no other live connId.<br/>PUBLISH conn_left (a1, alice, userGone true)
    R-->>NC: conn_left (a1, alice, userGone true)
    NC-->>Carol: drop a1 caret and alice's avatar
    Note over R: If every node left the doc, no sweep runs.<br/>The 90 s EXPIRE deletes the three keys, so nothing stays for good.
    end
```

## Timing budget

| Event | Mechanism | Worst case |
|---|---|---|
| Clean tab close | Close event, `LEAVE` script, publish | Milliseconds, well under 2 s. |
| Alice's browser dies without closing | Ping/pong timeout (20 s), then the leave path | About 30 s. |
| Node dies | Last refresh at most 10 s earlier, expiry 30 s after that, sweep every 5 s | About 35 s from the crash, under the 45 s limit. |
| Orphaned keys when nobody is left | `EXPIRE 90` on every key | 90 s after the last refresh. |

## Rules and rationale

- **Cursor identity is per connection.**
  - Cursors are identified by `connId`, and `seq` is a per-connection counter. A reconnect gets a new `connId`, so its `seq` starting again cannot clash with the old one.
  - The UI shows one caret per user: the connection whose cursor was applied most recently on that client. If that connection leaves, the user's other connection's caret shows.
- **Rate limit.**
  - The server keeps a per-connection monotonic timestamp and drops any cursor message that arrives less than 50 ms after the last accepted one.
  - The client spaces its sends at 60 ms to absorb network jitter. It sends the latest position on the trailing edge, so a drop is repaired by the next update.
- **No backwards jumps.**
  - Ordering uses the sender's own `seq`, not arrival order or revision.
  - A held cursor keeps one slot per `connId`, holding the highest `seq`. The shown caret is transformed forward each time a revision is applied.
  - A client never shows an older report after a newer one.
- **No gaps on join.** Subscribe, then snapshot, then buffer events. `seq` guards cursors and `join` is a set insert, so the overlap is harmless.
- **Volume.** The cost is at most 20 cursor writes per second per connection. Each is one `HSET` plus one `PUBLISH`, and the per-document key sizes are bounded by the number of connections.
- **Unchanged.** The edit path, the load balancer and the document service are not changed. The Postgres presence table and nightly cleanup job can be removed once clients use `presence_snapshot`.
