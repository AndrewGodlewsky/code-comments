# Live cursors and presence: design and sequence diagram

## Summary

Today the "who's here" list is a Postgres table that is updated on open and close and polled by clients every 30 s. Users on crashed nodes stay listed until a nightly job removes them, and there are no cursors.

In the new design each gateway node keeps the truth about its own connections in memory and writes a short-lived copy per document to the existing Redis. A joining client gets a snapshot from that copy, then live changes over a new pub/sub channel `pres:{docId}`, next to the existing `ops:{docId}`. Nothing new is added. The edit path, document service, Postgres and load balancer are untouched, and cursors never go through the document service or Postgres.

## Terms

- **Gateway node**: a server that holds browsers' WebSocket connections. Two people in the same document are usually on different nodes.
- **`connId` / `userId`**: `connId` is a random UUID, new for every connection. `userId` comes from the session. A user with two tabs has two connIds and one userId.
- **`localSockets`**: the in-memory map on each node, `docId` to its set of local connections.
- **Redis script**: a Lua script that a node runs inside Redis with one call (`EVAL`). Its writes and its publish happen together, so the keys and the pub/sub message never disagree. Its return value comes back to the calling node. JOIN, CURSOR, REFRESH, SWEEP and LEAVE are each one such script.
- **ZSET / HASH**: Redis sorted set (members with a score) and Redis map. Pub/sub only delivers to current subscribers and stores nothing.
- **`rev`, `appliedRev`**: `rev` is a document revision number. `appliedRev` is the last revision this client has applied. It only moves forward.
- **`transformPosition(pos, fromRev, toRev)`**: an existing editor function. It maps a character offset valid at `fromRev` to the same place at `toRev`, using the ops of the last 500 revisions that the client keeps locally. It throws `HistoryGone` when `fromRev` is older than that history, and the caller must then drop the position.
- **`seq`**: a counter per connection, set by the sender and rising with each cursor update. Receivers use it to ignore old or duplicate cursors.

## Where state lives

| State | Where | Written by | Refreshed or removed by |
|---|---|---|---|
| Socket, `connId`, `userId`, last cursor time, last cursor (`seq`, `rev`, `pos`) | Node memory (`localSockets`) | Owning node | Gone when the node dies. It is the source Redis is rebuilt from. |
| Liveness of each connection | Redis ZSET `pres:z:{doc}`, member `connId`, score = expiry (Redis `TIME` + 30 s) | JOIN script | Node heartbeat every 10 s. Removed by clean leave or by the sweep. |
| Who the connection is | Redis HASH `pres:i:{doc}`, `connId` to `userId, name, avatar` | JOIN script | Changed together with the ZSET by the same scripts. |
| Last cursor per connection | Redis HASH `pres:c:{doc}`, `connId` to `seq, rev, pos` | CURSOR script | Heartbeat re-writes it from the node's memory. Removed together with its ZSET entry. |
| Live changes | Pub/sub `pres:{doc}`: `join`, `cursor`, `conn_left` | The same scripts, atomically with the write | Not stored. |
| Held and shown carets, `lastSeq` per `connId` | Client memory | Client | Dropped on `conn_left`. |

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
    Note over NB: connId b1, userId bob (from the session).<br/>localSockets[doc1] += b1<br/>Only a connection that has opened doc1 may send cursors for it.
    NB->>R: SUBSCRIBE ops:doc1 and pres:doc1 (first local socket)
    Note over NB: Subscribe first, then read state.<br/>pres:doc1 events that arrive before the snapshot is sent are held by node B for b1,<br/>then sent to Bob right after the snapshot.<br/>Duplicates are harmless because every event is idempotent.
    NB->>R: JOIN script (doc1, b1, bob profile)
    Note over R: ZADD pres:z:doc1 (now+30s) b1<br/>HSET pres:i:doc1 b1 (bob, name, avatar)<br/>EXPIRE all three keys 90s.<br/>Reads the snapshot (live users and all cursors).<br/>If bob has no other live connId, PUBLISH join bob.
    Note over NB: If JOIN fails or Redis is unreachable, the doc still loads for Bob (the edit path does not use presence).<br/>Node B marks b1 as not joined, drops its cursors, and retries JOIN on its next 5 s tick.<br/>Bob sees no presence until it works, then gets the snapshot.
    R-->>NA: join bob
    NA-->>Alice: presence_join bob (avatar added)
    R-->>NC: join bob
    NC-->>Carol: presence_join bob
    R-->>NB: snapshot (the script's return value, not a pub/sub message)
    NB-->>Bob: presence_snapshot (full avatar list + carets)
    Note over Bob: Doc loads as today, appliedRev = 90.<br/>Each snapshot cursor goes through the caret rules in step 2.<br/>Idle users show because their cursor is stored, not streamed.
    end

    rect rgba(120,220,160,0.12)
    Note over Bob,Carol: 2. Alice moves her cursor
    Alice->>NA: cursor (doc1, seq 17, rev 88, pos 120)
    alt arrived less than 50 ms after the last accepted one on this connection
        NA--xAlice: silently dropped, no error, no Redis, no publish
    else accepted
        Note over NA: Node A keeps (seq, rev, pos) in memory for a1 so that REFRESH can re-write it.
        NA->>R: CURSOR script (a1, seq 17, rev 88, pos 120)
        Note over R: HSET pres:c:doc1 a1 (seq 17, rev 88, pos 120)<br/>PUBLISH pres:doc1 cursor (a1, alice, 17, 88, 120)
        R-->>NB: cursor a1
        NB-->>Bob: cursor (a1, alice, 17, 88, 120)
        R-->>NC: cursor a1
        NC-->>Carol: cursor (a1, alice, 17, 88, 120)
        R-->>NA: cursor a1
        NA-->>Alice: every node sends a cursor event to all its local sockets of doc1 except the sender's own connId a1<br/>(on node A: Alice's other tabs and any other users on A)
    end
    Note over NA: If the CURSOR call fails or times out, the node drops the update.<br/>No error goes to Alice and nothing is retried (a retry could deliver a stale position).<br/>Her next update, or the next heartbeat re-write, repairs it.
    Note over Bob: Caret rules on receipt:<br/>1. seq <= lastSeq[a1]: ignore (out of order or duplicate).<br/>2. Otherwise lastSeq[a1] = seq.<br/>3. rev > appliedRev: hold it, draw after that revision is applied.<br/>4. rev <= appliedRev: pos = transformPosition(pos, rev, appliedRev).<br/>5. HistoryGone: drop the caret until the sender's next update.<br/>Op flow is unchanged: remote_op advances appliedRev, then held carets are released.
    end

    rect rgba(255,200,120,0.14)
    Note over Bob,Carol: 3. Heartbeat and sweep (nothing goes through the document service)
    loop every 10 s on each node with local sockets on doc1
        NA->>R: REFRESH script (doc1, local connIds, last cursors from node memory)
        NB->>R: REFRESH script (doc1, local connIds, last cursors from node memory)
        Note over R: ZADD each connId with score now+30s (upsert).<br/>Re-writes info and cursor hashes.<br/>EXPIRE 90s on all three keys.
    end
    Note over Alice: On her own 10 s client timer (not tied to the heartbeat), if appliedRev has moved since her last report<br/>she re-sends her cursor (pos transformed to appliedRev, new seq).<br/>This keeps stored carets inside the 500-revision history for late joiners.
    loop every 5 s on each node with local sockets on doc1 (own timer, every node runs it)
        NB->>R: SWEEP script (doc1)
        Note over R: Removes entries with score below now from the ZSET, info and cursor hashes.<br/>PUBLISH conn_left for each, atomically with the removal.<br/>Usually removes nothing.
        NB->>R: read live users and cursors
        Note over NB: Compares Redis's users (userId) and cursors (connId to seq)<br/>with a record it keeps per local socket of what that socket was sent.<br/>Sends the missing joins, cursors and leaves.<br/>This repairs any lost pub/sub message within 5 s.
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
    Note over NA: Killed with no cleanup.<br/>Alice's sockets drop and pres:z:doc1 still holds a1 with score = last heartbeat + 30s.<br/>Its Redis connection closes, so Redis drops its subscriptions by itself.
    NA--xR: heartbeats stop
    Note over R: a1 stays in Redis until its score passes.<br/>Nothing is published and nothing is yet visible to others.
    Note over Alice: Her tabs reconnect through the load balancer to other nodes with new connIds.<br/>While a1 lingers she still appears once in the list (it is keyed by user).<br/>The caret applied most recently is the one shown.
    loop every 5 s until the score expires
        NC->>R: SWEEP script (doc1)
        Note over R: nothing expired yet
    end
    NC->>R: SWEEP script (doc1)
    Note over R: a1 is expired.<br/>ZREM, HDEL info and cursor.<br/>If alice has no other live connId: PUBLISH conn_left (a1, alice, userGone true).<br/>If her reconnected tab is live: userGone false and only the a1 caret is dropped.
    R-->>NC: conn_left (a1, alice, userGone true)
    NC-->>Carol: drop a1 caret and alice's avatar
    Note over R: If every node left the doc, no sweep runs.<br/>The 90 s EXPIRE deletes the three keys, so nothing stays for good.
    end
```

## Rules

- **Per user, not per tab.** The avatar list is keyed by `userId` and the ZSET by `connId`. `join` is published only when the user had no other live connection. `conn_left` carries `userGone`, true only when the user's last connection went. A client removes an avatar only when `userGone` is true.
- **Cursor identity is per connection.** Cursors are identified by `connId`, and `seq` is per connection. A reconnect gets a new `connId`, so a restarted `seq` cannot clash with the old one. The UI shows one caret per user: the connection whose cursor was applied most recently on that client. If that connection leaves, the user's other connection's caret shows.
- **Rate limit.** The server keeps a per-connection monotonic timestamp and drops any cursor that arrives less than 50 ms after the last accepted one. The client sends at most one per 60 ms (slack for network jitter), always the latest position on the trailing edge, so a drop is repaired by the next update. The cost is at most 20 cursor writes per second per connection, each one `HSET` plus one `PUBLISH`.
- **No backwards jumps.** Ordering uses the sender's own `seq`, not arrival order or revision. A held cursor keeps one slot per `connId`, holding the highest `seq`. The shown caret is transformed forward each time a revision is applied.
- **No gaps on join.** Subscribe, then snapshot, then send held events. `seq` guards cursors and `join` is a set insert, so the overlap is harmless.
- **No permanent leftovers.** All three keys have `EXPIRE 90`, refreshed on every join and heartbeat. A document nobody is in empties itself.
- **Redis failover.** Heartbeats upsert with `ZADD` (not `XX`) and re-write the info and cursor hashes. A replica that missed writes is repaired within 10 s.
- **Clock.** Scripts use Redis `TIME`, so nodes' clocks do not matter.

## When things fail

| Failure | What happens |
|---|---|
| JOIN fails or Redis is unreachable | Doc loads without presence. Node retries JOIN every 5 s. |
| CURSOR call fails | Update dropped, no retry. The next update or heartbeat repairs it. |
| Pub/sub message lost | The 5 s sweep compare sends what the socket missed. |
| Client WebSocket drops | Client reconnects and sends `Open` again. It gets a new `connId` and a new snapshot, and replaces its whole avatar list, carets and `lastSeq` values. The old `connId` goes by the leave path or the sweep. |
| A node's Redis subscription drops | On resubscribing, the node runs the same read-and-compare as the sweep at once for each of its documents. |
| Browser dies without closing | The node pings every 10 s and closes after 20 s without a pong, then takes the leave path. About 30 s. |
| Node dies | See step 5. The last refresh was at most 10 s before the crash and sets expiry 30 s ahead. The sweep runs every 5 s and finds it at most 5 s later. About 35 s, under the 45 s limit. |
| Nobody left in the doc | `EXPIRE 90` removes the keys, at most 90 s after the last refresh. |

A clean tab close takes milliseconds, well under the 2 s limit.

## Rollout

The edit path, the load balancer and the document service are not changed. The Postgres presence table, its 30 s polling and the nightly cleanup job can be removed once clients use `presence_snapshot`.

## Open questions

- Where do the name and avatar in the JOIN script come from? The gateway doc says only that `userId` comes from the session. If the session lacks them, node B needs a profile lookup, and a failed lookup should fall back to the `userId` and a default avatar. Not yet confirmed.
