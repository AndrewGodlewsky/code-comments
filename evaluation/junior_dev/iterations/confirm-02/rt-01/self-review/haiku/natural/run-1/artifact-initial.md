# Live cursors and presence: sequence design

Presence is built on the Redis primary that gateways already use. No new service, no change to the edit path or the load balancer. The Postgres presence table, its 30 s client polling and the nightly cleanup job are removed. Membership is a lease per connection, refreshed by heartbeat. Carets are ephemeral per-user hashes in Redis with a 30 s TTL. Pub/sub carries change hints only, and every hint is followed by a re-read of Redis state.

```mermaid
sequenceDiagram
    autonumber
    participant Bob as Bob browser
    participant GB as Gateway B
    participant R as Redis primary
    participant GA as Gateway A
    participant Alice as Alice browser
    participant Carol as Carol browser

    Note over Alice,Carol: Start state: Alice and Carol are open on Gateway A. Each has a presence doc member and a presence conn hash in Redis.

    Note over Bob,R: 1. Bob joins on Gateway B while Alice is already in the doc on Gateway A
    Bob->>GB: open doc
    GB->>R: SUBSCRIBE presence and cursor channels for doc, once per doc
    GB->>R: ZADD presence doc, member connBob, score now plus 30 s
    GB->>R: HSET presence conn connBob with userId, PEXPIRE 30 s
    GB->>R: PUBLISH presence hint join
    GB->>R: ZRANGEBYSCORE members with score at or above now, HMGET conns, HGETALL caret per user
    R-->>GB: live members, users, last caret of each user
    GB-->>Bob: presence snapshot deduped by userId, with Alice and Carol at their last carets
    Bob->>GB: cursor with pos and rev, sent right after open
    GB->>R: HINCRBY caret seq, HSET caret pos and rev, PEXPIRE caret 30 s
    GB->>R: PUBLISH cursor channel message
    R-->>GA: hint join
    GA->>R: re-read members and HMGET conns
    GA-->>Alice: presence snapshot now includes Bob

    Note over Alice,GB: 2. Alice moves her caret. The gateway allows one accepted cursor per 50 ms per connection.
    Alice->>GA: cursor with pos 812 and rev 40
    alt Under 50 ms since last accepted cursor on this connection
        Note over GA: Dropped silently. Never reaches Redis.
    else Accepted
        GA->>R: HINCRBY caret alice seq, HSET caret pos and rev, PEXPIRE caret 30 s
        GA->>R: PUBLISH cursor channel message with userId, seq, pos, rev
        R-->>GB: cursor message
        Note over GB: Drop if seq is not above the last shown seq for Alice. If rev is above applied rev, hold. Otherwise transform pos forward to applied rev.
        GB-->>Bob: draw Alice caret at applied rev
    end

    Note over GA,GB: 3. Heartbeat. Every 10 s each gateway refreshes every local connection.
    loop Every 10 s, per gateway, per local connection
        GA->>R: ZADD presence doc, connAlice, score now plus 30 s, returns 0
        GA->>R: HSET conn connAlice, PEXPIRE conn 30 s, EXPIRE presence doc 60 s, PEXPIRE caret 30 s
        GB->>R: ZADD presence doc, connBob, score now plus 30 s, returns 0
        GB->>R: HSET conn connBob, PEXPIRE conn 30 s, EXPIRE presence doc 60 s, PEXPIRE caret 30 s
    end

    Note over Carol,R: 4. Carol closes her tab cleanly
    Carol->>GA: socket close
    GA->>R: ZREM presence doc, connCarol
    GA->>R: DEL presence conn connCarol
    GA->>R: PUBLISH presence hint leave
    R-->>GB: hint leave
    GB->>R: re-read members and HMGET conns
    GB-->>Bob: snapshot without Carol, her caret removed
    R-->>GA: hint leave
    GA->>R: re-read members and HMGET conns
    GA-->>Alice: snapshot without Carol

    Note over GA: 5. Gateway A crashes. It runs no cleanup. Alice's socket dies.
    Note over R: Nothing refreshes Alice's conn hash, caret hash or ZSET score. Her conn and caret keys expire 30 s after the last heartbeat. Her ZSET member stays until a sweep removes it.
    loop Every 10 s, on each gateway that holds local sockets for the doc
        GB->>R: ZRANGEBYSCORE presence doc from -inf to now, expired members
        R-->>GB: connAlice
        GB->>R: ZREM presence doc, connAlice
        Note over GB: Publish leave only if ZREM returned 1, so exactly one node announces it
        GB->>R: PUBLISH presence hint leave
    end
    R-->>GB: hint leave
    GB->>R: re-read members and HMGET conns
    GB-->>Bob: snapshot without Alice, her caret removed
```

## Where state lives

| State | Where | Written by | Refreshed by | Removed by |
|---|---|---|---|---|
| Membership, one entry per connection | Redis ZSET `presence:doc:{docId}`, member connId, score = lease deadline | Node on open, on heartbeat, on clean close | Heartbeat every 10 s sets score to now plus 30 s. Key TTL 60 s, refreshed by heartbeat | Clean close: ZREM. Crash: any surviving node with local sockets on the doc sweeps expired scores and ZREMs them |
| Identity per connection (userId, name, colour) | Redis HASH `presence:conn:{connId}`, TTL 30 s | Node on open | Heartbeat | Clean close: DEL. Crash: TTL expiry |
| Caret per user (seq, pos, rev) | Redis HASH `presence:caret:{docId}:{userId}`, TTL 30 s | Node on each accepted cursor. Client sends an initial cursor on open | Heartbeat for local users | TTL expiry. Clients draw only users in the current list |
| Change hints | Pub/sub `presence:doc:{docId}` and `cursor:doc:{docId}` | Nodes | Not stored | Not stored. Subscribe only while the node has local sockets on the doc |
| Rate limit | Node memory, lastAcceptedAt per connId | Node | Each accepted cursor | Connection close |
| Client view | Presence list, lastSeq per userId, held carets | Client | Snapshots and cursor messages | Snapshot without the user |

Nothing is left in Redis for good. Every key has a TTL. A doc with no live connections has its ZSET expire after 60 s.

## Timing budgets

- **Clean leave:** ZREM and PUBLISH happen in the close handler, and other nodes re-read at once. Well under 2 s.
- **Node crash:** the last heartbeat was at most 10 s before the crash, so the lease ends at most 30 s after the crash. The next sweep runs at most 10 s later. Worst case is 40 s, inside the 45 s budget.
- **Join:** the snapshot comes from Redis on the joining node, not from pub/sub history, so no join is ever missed.

## Client rules (revisions and ordering)

- Each caret carries a per-user `seq` assigned by the node with HINCRBY, so it is monotonic across that user's tabs.
- Drop any caret whose seq is not above the last seq shown for that user. This is the no-backwards-jump rule and covers out-of-order arrival.
- If `rev` is above `appliedRev`, hold the caret. Keep only the highest-seq held caret. Draw it when `appliedRev` reaches `rev`.
- If `rev` is at or below `appliedRev`, call `transformPosition(pos, rev, appliedRev)`. On `HistoryGone`, drop the position and hide the caret until the next update. After each applied batch, move the shown caret to the current `appliedRev`, so it never needs its original revision again.
- Draw a caret only for users in the current presence list. Carets whose user has left disappear with the list.

## Other notes

- **Client coalescing.** The gateway drops anything within 50 ms and says nothing. The client must keep the latest pending caret and send it when the window opens. Otherwise the final move in a burst is lost and the caret stays wrong until the next move.
- **One user, two tabs.** The list is deduplicated by userId when the snapshot is built. The user stays listed until their last connection's lease goes. There is one caret per user, and the seq is per user, so no ordering problem arises between tabs.
- **Hints, not events.** Receivers re-read Redis on every hint instead of trusting the message body. Out-of-order or duplicate hints cannot leave a wrong list.
- **Re-add after a stall.** If a heartbeat arrives after a sweep has removed the member, ZADD returns 1. The node then publishes join again. A stalled node causes a brief flicker, not a leak.
- **Lost pub/sub messages.** Missed cursor messages are harmless. The next move corrects the caret, and joins read state from Redis.
- **Primary reads.** Presence reads go to the Redis primary, not the replica, so a fresh join is not hidden by replica lag. After a failover, heartbeats rebuild lost state within 10 s.
- **Idle users.** Their carets persist because the caret hash is refreshed by heartbeat, not by movement. Every client sends an initial cursor on open, so a user who never moves still has a caret for joiners.
- **Unchanged.** The edit path, the load balancer and the document service are untouched. Postgres loses only the presence table.
