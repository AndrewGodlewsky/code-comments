# Live cursors and presence: design

## Summary

Presence (who is in a document) and cursors (where their carets are) live in Redis, which all gateway nodes share. Redis is already deployed and is the only infrastructure involved. The edit path, document service, Postgres and load balancer are not touched.

Why Redis: two people in the same document are usually on different gateway nodes, so no single node knows the whole picture. Redis holds the shared state, and its pub/sub carries changes between nodes.

How it works:
- Each WebSocket connection is a member of a Redis sorted set, scored by the time it expires. Its node pushes that expiry forward every 10 s.
- Each connection's latest cursor is stored in a Redis hash.
- Every change is published on one pub/sub channel per document, `pres:{doc}`. Each node forwards those events to its local browsers.
- If a node dies, its members stop being renewed and expire. Surviving nodes then remove them.

Terms:
- `doc`: the document id (`docId` in the existing protocol). A key written `{doc}` exists once per document.
- `connId`: the random id of one WebSocket connection. A user with two tabs has two `connId`s.
- `userId`: comes from the session. It must not contain `|`, which holds for UUIDs.
- `rev`: a document revision number. `appliedRev`: the last revision a given client has applied.
- Node: a gateway server process. Client: the browser editor.

## Where state lives

| State | Lives in | Written by | Refreshed by | Removed by |
|---|---|---|---|---|
| Live connections per doc | Redis sorted set `pexp:{doc}`. Member is `userId\|connId`, score is its expiry time in ms. | Node's `join` script | Heartbeat every 10 s (expiry = now + 30 s) | Clean `leave`, or `sweep` once the score is in the past. The key also has `EXPIRE 60 s`, renewed by every write. |
| Latest cursor per connection | Redis hash `cur:{doc}`. Field is `connId`, value is `{userId, n, rev, pos, ts}`. | Node's `cursor` script, only if `n` is greater than the stored `n` | Each cursor update. The heartbeat renews the key's TTL. | `leave`, `sweep`, or key TTL |
| Presence change counter | Redis `pseq:{doc}` | Incremented by `join`, `leave` and `sweep` | Same TTL as the other keys | Key TTL |
| Change feed | Redis pub/sub channel `pres:{doc}`, carrying `join`, `leave` and `cursor` events. It stores nothing. | The Lua scripts, so event order matches state order | n/a | n/a |
| `localSockets`, per-connection `lastCursorAt`, `connId` to `userId` | Node memory | Node | Node | Socket close, or the node dying |
| Applied revision, shown carets, held cursors, `lastN[connId]`, snapshot `seq` | Client memory | Client | n/a | Tab close |

Cursor fields: `n` is a per-connection counter that only increases, `rev` is the sender's applied revision, `pos` is a character offset valid at `rev`, and `ts` is the server time of the update.

Mechanics:
- **Scripts.** The node does all Redis writes through five Lua scripts: `join`, `cursor`, `heartbeat`, `leave` and `sweep`. A Lua script runs atomically inside Redis, so no other command interleaves with it. It reads time from Redis `TIME`, so node clocks do not matter, and it publishes its event from inside the script. This keeps events in the same order as the state changes.
- **Channel subscription.** A node subscribes to `pres:{doc}` at the same moment it subscribes to `ops:{doc}`, when the first local socket opens the doc. It unsubscribes from both when the last local socket closes.
- **Replaced and unchanged.** The old Postgres presence table, the 30 s polling and the nightly cleanup job go away. Nothing else existing changes.

## Rules that make it correct

- **Per user, not per tab.**
  - Each connection is its own sorted-set member. `join` and `leave` check whether another live member with the same `userId` exists.
  - Every event carries `connId`. `join` and `leave` also carry `first` (this is the user's first connection) and `last` (it was their last).
  - Clients add an avatar when `first=true` and remove it only when `last=true`.
  - Carets are per connection. Each avatar shows the caret with the highest `ts`.
- **Join without gaps.**
  - The node subscribes to `pres:{doc}` before it runs `join`, so no event can fall between the snapshot and the live feed.
  - `join` returns a snapshot in the same atomic step as its own publish. The snapshot holds the live users, every stored cursor, and `seq` (the value of `pseq` after this join).
  - The client drops any `join` or `leave` event with `seq <= snapshot.seq`, because the snapshot already includes it.
  - Idle users' carets arrive in the snapshot, because each connection's last cursor stays in `cur:{doc}`.
- **Cursor rate.**
  - The client sends at most one update per 60 ms, plus a trailing send so the final position is not lost. The 60 ms leaves margin for network jitter.
  - The node compares the server arrival time with the connection's `lastCursorAt` and silently drops anything under 50 ms after the previous accepted update. A dropped update never reaches Redis.
- **Revisions.**
  - The sender reports its position at its own `appliedRev`. If it has local edits not yet acked, it maps the position back through them, or waits for the ack.
  - A receiver never draws a caret at a revision it has not applied. It holds the newest such cursor per `connId` and draws it when `appliedRev` reaches that revision.
  - A cursor with `rev < appliedRev` is drawn at `transformPosition(pos, rev, appliedRev)`.
  - If `transformPosition` throws `HistoryGone`, the caret is dropped until the sender's next update.
  - A caret that is already shown is transformed forward on each applied `remote_op`.
- **No backwards jumps.**
  - Each connection stamps its cursors with a counter `n` that only increases.
  - The receiver keeps `lastN[connId]` and ignores any cursor with `n <= lastN`. This covers messages that arrive late or out of order, and a held cursor that a newer one replaces. Redis applies the same rule to what it stores.
  - A cursor for a `connId` that has already left is ignored.
- **Clean leave.** `leave` runs when the socket closes, and the event reaches other users in milliseconds, well inside 2 s. A graceful node shutdown runs `leave` for every local connection.
- **Node crash.**
  - A dead node stops renewing its members, so their scores run out within 30 s of the last heartbeat.
  - Every node that still has local sockets on a doc runs `sweep` for it every 5 s. The script removes expired members and their cursors, and publishes `leave` with `last=true` for each user with no live member left. Because the script is atomic, only one node publishes each removal.
  - Worst case is about 35 s (30 s expiry plus up to 5 s until the next sweep), against the 45 s limit.
  - If no node has a socket on the doc, nobody needs the removal, and the `EXPIRE 60 s` on the keys clears them. Nothing stays in Redis for good.
- **Redis failover or a paused node.** After a failover (the replica may lack recent writes), or a pause long enough for members to expire, members can go missing. The heartbeat uses `ZADD XX`, which only renews members that still exist, and returns the missing `connId`s. The node re-runs `join` for them without announcing anything new (no `join` event is published), and restores their last cursors.

## Sequence diagram

Setup: Alice has one connection, `c1`, on node N1. Carol has one connection, `c3`, on node N3. Bob joins on node N2 with his first connection, `c2`. Alice's and Carol's cursors are already stored in `cur:doc`. The document service and Postgres do not appear because they are not involved. The diagram writes `doc` for the document id.

```mermaid
sequenceDiagram
    autonumber
    participant A as Alice client (conn c1)
    participant N1 as Node 1
    participant R as Redis (pexp, cur, pseq, pres channel)
    participant N2 as Node 2
    participant B as Bob client (conn c2)
    participant N3 as Node 3 (Carol, conn c3)

    Note over A,N3: Before: c1 on N1 and c3 on N3 are in pexp. N1 and N3 are subscribed to pres:doc. pseq is 7. cur holds the c1 and c3 carets.

    rect rgb(235,245,255)
    Note over B,R: JOIN (Bob, first connection, node N2)
    B->>N2: open docId
    N2->>N2: check cookie, assign connId c2, add to localSockets
    N2->>R: SUBSCRIBE ops:doc and pres:doc (first local socket on this doc)
    N2->>R: EVAL join: ZADD pexp bob|c2 exp=now+30s, INCR pseq to 8, EXPIRE 60s, PUBLISH join first=true
    R-->>N2: snapshot: seq 8, users, all stored cursors with rev, n and pos
    N2-->>B: presence_snapshot
    Note over B: Draw avatars. For each cursor: if rev is above appliedRev, hold it. Otherwise transformPosition to appliedRev (on HistoryGone, drop it). Set lastN[connId].
    R--)N1: pres join bob c2 first=true seq 8
    N1-->>A: presence_join (Alice adds Bob)
    R--)N3: pres join bob c2 first=true seq 8
    R--)N2: pres join seq 8
    N2-->>B: Bob's own join event. Its seq 8 is not above the snapshot seq 8, so Bob's client drops it.
    end

    rect rgb(240,255,240)
    Note over A,B: CURSOR MOVE (ephemeral, never reaches the document service or Postgres)
    A->>N1: cursor n=41 rev=120 pos=57 (client sends at most one per 60 ms)
    alt arrives under 50 ms after the last accepted one from c1
        N1--xN1: silently dropped, nothing reaches Redis
    else accepted
        N1->>R: EVAL cursor: if 41 is above the stored n then HSET cur c1, EXPIRE 60s, PUBLISH cursor
        R--)N2: pres cursor c1 n=41 rev=120 pos=57
        N2-->>B: cursor c1 n=41 rev=120 pos=57
        alt n is at most lastN[c1] (late or duplicate)
            Note over B: ignore, never move a caret back
        else rev 120 is above Bob's appliedRev 118
            Note over B: record lastN=41, hold the cursor, draw nothing yet
            R--)N2: ops:doc remote_op rev 119 then 120 (edit path, unchanged)
            N2-->>B: remote_op 119 and 120
            Note over B: appliedRev reaches 120, so draw Alice's caret at 57
        else rev is at most appliedRev
            Note over B: record lastN=41, draw at transformPosition(57, rev, appliedRev). On HistoryGone, drop the caret.
        end
    end
    end

    rect rgb(255,250,230)
    Note over N1,R: HEARTBEAT and SWEEP (loops, independent of clients)
    loop every 10 s on every node, per doc with local sockets
        N1->>R: EVAL heartbeat: ZADD XX each local member with exp=now+30s, EXPIRE pexp, cur and pseq 60s
        R-->>N1: list of missing connIds (normally empty)
        opt a member is missing (Redis failover or long pause)
            N1->>R: EVAL join again for those connIds, restoring their last cursors
        end
    end
    loop every 5 s on every node with local sockets on the doc
        N2->>R: EVAL sweep: remove expired members and their cursors, INCR pseq, PUBLISH leave last=true per fully gone user
        R-->>N2: nothing expired (normal case)
    end
    end

    rect rgb(255,240,240)
    Note over B,A: CLEAN LEAVE (Bob closes his last tab, visible within 2 s)
    B->>N2: WebSocket close
    N2->>R: EVAL leave c2: ZREM pexp, HDEL cur c2, INCR pseq to 9, PUBLISH leave last=true
    N2->>R: UNSUBSCRIBE pres:doc and ops:doc (no local sockets left)
    R--)N1: pres leave bob c2 last=true seq 9
    N1-->>A: presence_leave (avatar and caret removed)
    R--)N3: pres leave bob c2 last=true seq 9
    Note over R: If Bob had a second tab, last=false: his avatar stays and only that tab's caret goes.
    end

    rect rgb(250,235,255)
    Note over N3,A: NODE CRASH (Carol's node N3 dies, no cleanup)
    N3--xN3: process killed, heartbeats stop
    Note over R: The pexp score for carol|c3 stays at the last renewal plus 30 s. cur c3 stays until swept.
    loop every 5 s
        N1->>R: EVAL sweep
    end
    Note over N1,R: within 35 s the score is in the past
    N1->>R: EVAL sweep: ZREM carol|c3, HDEL cur c3, INCR pseq to 10, PUBLISH leave last=true
    R--)N1: pres leave carol c3 last=true seq 10
    N1-->>A: presence_leave (Carol and her caret removed, under 45 s)
    Note over R: If no node still had a socket on this doc, nothing sweeps. The 60 s EXPIRE on pexp, cur and pseq clears everything, so nothing is left for good.
    end
```

## Timings

| Event | Detection | Visible to others |
|---|---|---|
| Clean tab close | Immediate | Milliseconds (limit 2 s) |
| Node crash | Score expiry (last heartbeat + 30 s), plus up to 5 s until the next sweep | About 35 s (limit 45 s) |
| Dead socket on a live node | Ping/pong timeout of 20 s, then `leave` | About 20 s |
| Redis failover | Next heartbeat (within 10 s) re-adds the members | No visible change if the failover is fast enough |

## Left open

- **Several tabs per user.** The design assumes that showing the most recently moved tab's caret is acceptable. Showing every tab's caret would need no protocol change, only a client choice.
- **Load.** Cursor traffic costs one Redis script call per accepted update, at most about 17 per second per user (one per 60 ms). If Redis becomes the bottleneck, nodes could coalesce updates per connection, but that is not needed for the requirements.