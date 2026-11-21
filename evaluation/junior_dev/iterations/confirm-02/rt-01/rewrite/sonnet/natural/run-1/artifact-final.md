# Live cursors and presence: design

## Summary

Today, "who's here" is a Postgres table that is written on open and close, polled by clients every 30 s, and cleaned nightly, so users on crashed nodes stay listed until the next night, and there are no cursors. The new design keeps all presence and cursor state in Redis, which the gateway already uses. A joining node runs an atomic Lua script that adds the connection and returns a snapshot of everyone present plus their last cursors. After that, changes travel live on a pub/sub channel `pres:{docId}`. Every entry expires unless its node keeps refreshing it, so a dead node's users vanish without any cleanup from the dead node. The edit path, the load balancer and the document service are unchanged, there is no new infrastructure, and nothing about presence or cursors is ever written to Postgres.

## Terms

- **Gateway node**: a server that holds browsers' WebSocket connections. Six today, autoscaled, and killable at any time with no cleanup. People in one document are usually on different nodes.
- **`connId` / `userId`**: `connId` is a random UUID, new for every connection. `userId` comes from the session. One user with two tabs has one `userId` and two `connId`s.
- **`localSockets`**: each node's in-memory map of `docId` to its local connections.
- **Pub/sub**: Redis broadcast. It delivers only to current subscribers and stores nothing. This is why cursors are also stored in a hash, so that a joiner can see idle users' carets.
- **ZSET / HASH**: Redis sorted set (members with a numeric score) / Redis key-to-value map.
- **Lua script**: code that Redis runs atomically. It can read the Redis clock (`TIME`) and publish. There are five: `join`, `touch`, `cursor`, `leave`, `reap`.
- **Entry**: one `userId|connId` member of the `pres:{docId}` ZSET. Its score is its expiry time.
- **Reap**: remove entries whose expiry has passed.
- **`_n` and `v`**: `_n` is one counter per document, stored in `cur:{docId}`. Each presence event takes the next number as its `v`, inside the same script that publishes it. Receivers use `v` to discard stale or duplicate messages.
- **Snapshot**: what `join` returns: the live users, their profiles, their last cursors, and the current `n`.
- **`minV`**: the snapshot's `n`, stored on the connection. The node forwards only events with `v > minV`.
- **`appliedRev`**: the last document revision this client has applied. It only moves forward.
- **`transformPosition(pos, fromRev, toRev)`**: existing client function. It maps a character offset valid at `fromRev` to the same place at `toRev`, where `fromRev <= toRev <= appliedRev`. The client keeps the last 500 revisions of ops. If `fromRev` is older than that, it throws `HistoryGone`, and the caller must drop the position.
- **Held cursor**: a cursor whose `rev` is above `appliedRev`. The client stores it and draws nothing until it has applied that revision.
- **`lastV[user]`**: on the client, the highest cursor `v` seen for that user.

## Where state lives

| State | Location | Created by | Refreshed by | Removed by |
|---|---|---|---|---|
| Socket, `connId`, `userId`, `minV`, `lastCursorAt` | Node memory (`localSockets`) | WebSocket connect | None | Socket close, or node death |
| Subscription to `pres:{docId}` | Node, per document | First local socket on the document | None | Last local socket closes, or node death |
| `pres:{docId}`: ZSET, member `userId\|connId`, score = expiry in ms | Redis primary | `join` | `touch`, every 10 s (new score = Redis `TIME` + 30 s) | `leave`, `reap`, or key TTL |
| `cur:{docId}`: HASH with `_n`, `c:<userId>` = `{rev,pos,v}`, `p:<userId>` = profile | Redis primary | `join` (profile), `cursor` | `EXPIRE 120` on every script call | `leave` or `reap` when the user's last entry goes, or key TTL |
| Presence list, `lastV`, held cursors, drawn carets `(pos, atRev)`, `appliedRev` | Client memory | Snapshot, then live events | Live events | Reconnect (rebuilt from a new snapshot) |
| Anything about presence or cursors | Postgres | Never | N/A | N/A |

| Timing | Value |
|---|---|
| Heartbeat (`touch`) | every 10 s |
| Entry expiry | 30 s after the last `touch` |
| Sweep (`reap`) | every 5 s, by every node that has a local socket on the document |
| Key TTL (backstop) | 120 s |
| Existing WebSocket ping/pong | unchanged: ping every 10 s, close if no pong in 20 s |
| Client cursor sends | at most one per 60 ms |
| Server cursor limit | at least 50 ms between accepted cursors per connection |

Requirements met by these numbers: after a clean tab close, others see the change within 2 s. After a node dies, its users leave everyone's list within 45 s (expiry 30 s plus up to 5 s until the next sweep is 35 s at most).

Two infrastructure rules:
- **Redis `TIME`, not node clocks.** Entry scores come from Redis `TIME` inside the scripts, so clock skew between nodes does not matter.
- **Primary only.** All scripts and reads go to the Redis primary, never the replica, because a stale snapshot would break the `v` ordering. If Redis is ever clustered, the keys need a `{docId}` hash tag.

## How it runs

The diagram shows one scenario. Bob is on node N2. Alice joins on N1 with applied revision 117, moves her cursor, opens a second tab, closes both tabs, and later reopens the document and N1 crashes.

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

### Steps in detail

The diagram shows the order of messages. These notes add the rules and failure handling that it cannot show.

1. **Join.** Trigger: a client opens a document. The node subscribes to `pres:{docId}` first (if this is its first local socket on the document), then runs `join`.
   - `join` first reaps expired entries, then does `ZADD`. It stores the profile and publishes `join` only if this is the user's first live entry. A second tab of the same user publishes nothing. It always returns a snapshot. Profile data (name, avatar) is taken from the session and kept in `p:<userId>`. Caret colour is derived from `userId`.
   - The "does this user already have an entry" check scans the document's `pres` set. That is cheap, because a document has tens of connections.
   - The node sends the snapshot to the client and sets `conn.minV = n`. It then forwards only events with `v > minV`. This is why the node does not echo the join event from its own publish.
   - The client replaces its whole list with the snapshot, and clears `lastV` and held cursors. It applies later events only if `v > snapshot.n`.
   - Failure: if Redis is down, the join fails and the editor still works (see the failure table).
2. **Cursor update.** Trigger: the user moves the caret.
   - **Client sends** `{t:"cursor", docId, rev: appliedRev, pos}` at most once per 60 ms. The margin over 50 ms covers network bunching. A trailing send always goes out, so the final position is sent. One extra re-send happens 1 s after the last move, to repair a final update the server dropped, which would otherwise leave an idle caret stale.
   - **Node checks** that at least 50 ms have passed since the last accepted cursor on that connection (monotonic clock). Otherwise it drops the message silently. Accepted messages go to the `cursor` script. They never go through the document service and never reach Postgres.
   - **`cursor` script** does nothing if `userId|connId` is not in `pres`. Otherwise it increments `_n`, stores `c:<user>` and publishes `cursor {userId, rev, pos, v}`.
   - **Nodes** forward the event to their local sockets, except that a user's own cursor is never sent back to that user.
   - **Receiving client**, in this order:
     1. If `v <= lastV[user]`, drop it, whatever order messages arrive in. Otherwise set `lastV[user] = v`. Only the newest cursor per user is kept, held or drawn.
     2. If `rev > appliedRev`, hold it and draw nothing. After each applied remote op, draw any held cursor whose `rev <= appliedRev`.
     3. If `rev < appliedRev`, draw at `transformPosition(pos, rev, appliedRev)`. If it throws `HistoryGone`, drop the position and hide that caret until the next update.
     4. On every applied op, re-transform each drawn caret from its `atRev`, so no drawn caret falls outside the 500-revision history.
3. **Heartbeat and sweep.** Trigger: timers on each node.
   - Every 10 s, for each document and user with local connections, the node runs `touch` with that user's `connId`s. `touch` is `join` without the snapshot: it sets the score to `TIME + 30 s` and `EXPIRE 120`. If Redis lost an entry (failover or a stalled node), `touch` re-adds it and announces the join if the user had vanished.
   - Every 5 s, every node with a local socket on the document runs `reap`. It normally removes nothing.
4. **Leave.** Trigger: a socket closes, cleanly or because the existing 20 s pong timeout fired. Both use the same path. The node runs `leave`.
   - `leave` and `reap` remove the entries. If the user has no entry left, they delete `c:<user>` and `p:<user>` and publish `leave {userId, v}`. Otherwise they publish nothing.
   - When the last local socket on a document closes, the node unsubscribes from `pres:{docId}`.
   - Receivers remove the avatar and caret.
5. **Node crash.** Trigger: a node is killed. It does no cleanup, so its entries stop being touched. Within 35 s, a sweeping node reaps them and publishes `leave` if the user has no other entry. If every node on the document died, nobody sweeps, but the 120 s key TTL deletes `pres:{docId}` and `cur:{docId}`, so nothing stays in Redis for good.
   - If a user reconnects to another node before the old entry expires, the new entry has a new `connId`. The old entry expires silently, because the user still has a live entry, so no leave is published.

## What happens when things fail

| Failure | Result |
|---|---|
| Client sends faster than 50 ms | Node drops the extra messages silently. The 1 s re-send repairs a dropped final position. |
| Messages arrive out of order or duplicated | Client drops any cursor with `v <= lastV[user]` and any event with `v <= snapshot.n`. |
| Cursor is for a revision the client has not applied | It is held, then drawn once that revision is applied. |
| `transformPosition` throws `HistoryGone` | The position is dropped and the caret hidden until the next update. |
| Cursor from a connection that is not in `pres` (expired or removed) | `cursor` script ignores it. |
| Redis lost an entry (failover, stalled node) | The next `touch` re-adds it and announces the join if needed. |
| Redis outage | Editing is unaffected, because the edit path does not use these scripts. Presence and cursors freeze. The next `touch` or `join` after recovery rebuilds them. |
| Client reconnects | It gets a new snapshot, which replaces its list and clears `lastV` and held cursors. |
| Node dies | See step 5: gone within 35 s, limit 45 s. |
| Every node on a document dies | Key TTL (120 s) deletes both keys. |

## Choices and limits

- **One caret per user.** Two tabs share one caret: the tab that moved last. If that tab closes while the other stays open, the caret stays at its last position until the other tab moves.
- **Cursor write cost.** The worst case is about 20 Redis writes per second per active user. This is the price of showing idle users' carets on join, because pub/sub alone stores nothing.

## Rollout

Retire the Postgres presence table, the 30 s client polling and the nightly cleanup job. The design adds no new infrastructure and makes no change to the edit path or the load balancer.

## Open questions

None. The one condition to remember is that a clustered Redis needs a `{docId}` hash tag on the keys.