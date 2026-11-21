# Live cursors and presence: sequence design

## What this is

Presence (who is in a document) and carets (where each person's text cursor is) run on the existing gateway nodes and the existing Redis. Redis holds this short-lived state, and its pub/sub channels pass updates between nodes. The edit path, the load balancer and Postgres do not change, and the document service is not involved. Cursors are never written to Postgres.

The main flow: a user opens a document, and their node records them in Redis and sends back the current list and carets. Cursor moves and heartbeats keep that state fresh. A clean close removes it at once. If a node crashes, the other nodes remove its users within 35 seconds.

Today the "who's here" list is a Postgres table. It is updated on open and close and polled by clients every 30 s. Crashed nodes stay listed until a nightly job removes them. There are no cursors. This design replaces the list and adds carets.

## Terms

- **Gateway node**: a server that holds browsers' WebSocket connections. There are six, autoscaled. The load balancer spreads new connections across them round-robin, so people in the same document are usually on different nodes. A killed node does no cleanup.
- **Document service**: the service that owns the document and Postgres. It gives each applied edit its revision number. It is not used here.
- **Connection (connId)**: one WebSocket connection, with a new random id each time. A user with two tabs has two connections.
- **User (userId)**: the user's id from their session cookie. It is the same across tabs.
- **Revision (rev)**: the number the document service gives each applied edit, in order.
- **appliedRev**: the highest revision this editor has applied. It only goes up.
- **Caret**: a text cursor position, as a character offset from the start of the document.
- **seq**: a counter that the sending client increases with each cursor it sends on one connection. A higher seq is newer.
- **transformPosition(pos, fromRev, toRev)**: an editor function that moves a caret offset from an older revision to a newer one. It needs the editor to still hold history back to fromRev, which is the last 500 revisions. If it throws HistoryGone, the caller drops the caret.
- **Heartbeat**: a refresh every 10 s that says a connection is still alive.
- **Sweep**: a cleanup that every node runs every 5 s to remove stale entries.
- **Nudge**: a short pub/sub message that means "something changed, re-read". It is only a hint.
- **Pub/sub**: Redis channels. A subscriber gets only the messages sent while it is subscribed. Redis stores nothing.
- **Sorted set (ZADD)**: a Redis set where each member has a score. Here the score is the time of the member's last heartbeat.
- **Hash (HSET)**: a Redis map from field to value. Here the field is a connId and the value is that connection's last caret.
- **EXPIRE**: a Redis timer that deletes a key after a set time. Here it is 60 s after the last write.

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant AB as Alice browser (tab a1)
    participant N1 as Gateway N1
    participant R as Redis
    participant N2 as Gateway N2
    participant BB as Bob browser (tab b1)
    participant N3 as Gateway N3
    participant CB as Carol browser (tab c1)

    Note over AB,N1: Alice is already in the doc. Her connection a1 is a member of presence:doc, and her last caret is in cursors:doc.

    rect rgb(235, 245, 255)
    Note over BB,R: 1. Bob joins on N2 while Alice is on N1
    BB->>N2: WebSocket open doc (cookie gives userId Bob, new connId b1)
    N2->>R: SUBSCRIBE presence:doc and cursor:doc
    Note right of N2: Subscribe first. Live frames for Bob are held until the snapshot has been sent.
    N2->>R: ZADD presence:doc score=now member=b1 (userId, name, colour), EXPIRE presence:doc 60
    N2->>R: ZRANGEBYSCORE presence:doc (now-30s) +inf
    N2->>R: HGETALL cursors:doc
    R-->>N2: members (Alice, Bob), cursor entries (Alice pos 97, rev 42, seq 7)
    N2-->>BB: presence_snapshot (users, cursors)
    Note right of BB: Bob has applied rev 42. Alice's caret is at rev 42, so it draws now. A caret at a later rev would be held.
    N2->>R: PUBLISH presence:doc joined b1
    R-->>N1: presence:doc joined b1
    N1->>R: ZRANGEBYSCORE presence:doc (now-30s) +inf
    N1-->>AB: presence_users (Alice, Bob)
    end

    rect rgb(240, 255, 240)
    Note over AB,BB: 2. Alice moves her cursor. Cursors never touch the document service or Postgres.
    AB->>N1: cursor (pos 118, rev 43, seq 8)
    Note over AB,N1: The client sends at most one cursor per 50 ms. It keeps a trailing timer so the last position is always sent.
    N1->>N1: throttle check. Under 50 ms since the last accepted update from a1 means silent drop.
    N1->>R: HSET cursors:doc a1 (pos 118, rev 43, seq 8)
    N1->>R: PUBLISH cursor:doc a1 (pos 118, rev 43, seq 8)
    R-->>N2: cursor:doc a1 (pos 118, rev 43, seq 8)
    N2-->>BB: cursor a1 (pos 118, rev 43, seq 8)
    Note right of BB: Rev 43 is ahead of Bob's applied rev 42. Bob holds the caret (seq 8 kept as the newest for a1).
    Note over R,N2: Edit path, unchanged: the doc service publishes rev 43 on ops:doc, and N2 forwards remote_op 43 to Bob.
    N2-->>BB: remote_op rev 43
    Note right of BB: Bob applies rev 43, then draws the held caret at 118.
    end

    rect rgb(255, 250, 230)
    Note over AB,CB: 3. Heartbeat and sweep (every node, for each doc it has sockets on)
    loop every 10 s, for each local connection
        N1->>R: ZADD presence:doc score=now member=a1, EXPIRE presence:doc 60, EXPIRE cursors:doc 60
        N2->>R: ZADD presence:doc score=now member=b1, EXPIRE presence:doc 60, EXPIRE cursors:doc 60
    end
    loop every 5 s, every node with local sockets on the doc
        N1->>R: ZREMRANGEBYSCORE presence:doc -inf (now-30s)
        N1->>R: HDEL cursors:doc for every connId no longer in presence:doc
        N1->>R: ZRANGEBYSCORE presence:doc (now-30s) +inf
        N1-->>AB: presence_users, only when the user list changed
    end
    end

    rect rgb(255, 240, 240)
    Note over BB,AB: 4. Bob leaves cleanly (tab closed)
    BB->>N2: close
    N2->>R: ZREM presence:doc member b1
    N2->>R: HDEL cursors:doc b1
    N2->>R: PUBLISH presence:doc left b1
    Note right of N2: Explicit removal plus a nudge. This is what makes the change arrive within 2 s.
    R-->>N1: presence:doc left b1
    N1->>R: ZRANGEBYSCORE presence:doc (now-30s) +inf
    N1-->>AB: presence_users (Bob removed, if he has no other connection)
    N1-->>AB: cursor_gone b1
    end

    rect rgb(245, 240, 255)
    Note over N3,CB: 5. Node N3 crashes while Carol (c1) is in the doc
    Note over N3: N3 dies. It does no cleanup. Carol's member and cursor stay in Redis, last heartbeat at t0 (at most 10 s before the crash).
    Note over R: Nothing refreshes Carol's entries after t0.
    CB->>N1: reconnect (new connId c2), handled like Bob's join
    loop every 5 s, on N1 and N2
        N1->>R: ZREMRANGEBYSCORE presence:doc -inf (now-30s) removes c1 once t0+30 s has passed
        N1->>R: HDEL cursors:doc c1
        N1-->>AB: presence_users (Carol gone, if no other connection)
    end
    Note over N1,AB: Removal happens by t0+30 s plus up to 5 s sweep lag, so at most 35 s after the crash. This is inside the 45 s limit.
    Note over R: If no node with sockets remains, presence:doc and cursors:doc expire 60 s after their last write. Nothing stays in Redis for good.
    end
```

## Steps

The diagram shows the order. These steps add the trigger, the state and the failure for each part.

1. **Join.** Trigger: a browser opens the document on a node. The node subscribes to `presence:doc` and `cursor:doc` first. Then it writes the user's member, reads the members and the cursor hash, sends `presence_snapshot`, and only then forwards live frames. Subscribing first means nothing is missed in the gap. Overlap may repeat a message, and the seq rule makes repeats harmless. Right after its open completes, each client sends one cursor, so idle users still have a caret stored in `cursors:doc`.
2. **Cursor move.** Trigger: the user moves the caret. The client sends at most one cursor every 50 ms and keeps a trailing timer so the last position gets through. The node drops any cursor that comes less than 50 ms after the last accepted one from that connection, with no message back. An accepted cursor is written to `cursors:doc`, then published on `cursor:doc`. Receivers apply the revision rules below. Text edits still use the unchanged edit path.
3. **Heartbeat and sweep.** Every 10 s, each node refreshes each of its local connections. It updates that member's score and sets EXPIRE 60 on `presence:doc` and `cursors:doc`. Every 5 s, each node with local sockets on the document sweeps. It removes members whose score is older than 30 s, deletes cursor fields whose connId is no longer a live member, and reads the live members again. It sends `presence_users` only when the user list changed. Several nodes can sweep at once. This is harmless, so no leader is needed.
4. **Clean leave.** Trigger: the tab closes cleanly. The node removes the member (ZREM), deletes the cursor (HDEL) and publishes a `left` nudge. Other nodes re-read the members, send `presence_users`, and send `cursor_gone` for that connId. The user disappears only if this was their last connection. Explicit removal plus the nudge makes the change arrive within 2 s. If the nudge is lost, the next sweep catches it within 5 s.
5. **Node crash.** Trigger: a node dies. It does no cleanup, so its members and carets stay with their last heartbeat time, t0. That is at most 10 s before the crash. Nothing refreshes them. The sweeps on the surviving nodes remove them once they are 30 s old, plus up to 5 s of sweep lag, so at most 35 s after the crash. The users reconnect to a live node and join as in step 1.

## Where state lives

| State | Location | Written by | Refreshed or removed by |
|---|---|---|---|
| Presence member, one per connection (userId, name, colour, connId) | Redis sorted set `presence:doc`, score = last heartbeat time | The node that owns the socket, on join | Heartbeat every 10 s. Removed by clean close (ZREM), or by sweep when the score is older than 30 s. The node keeps the member string exactly as written for the connection's life, because ZREM and ZADD need an exact match. |
| User list | Not stored. Distinct userIds among live members | Each receiving node, on read | Recomputed on every nudge and every 5 s sweep. A user is listed while any of their members is live. |
| Last caret per connection | Redis hash `cursors:doc`, field = connId | The node, on each accepted cursor | Removed on clean close, or by sweep when the connId is no longer a live member. Kept while the user is idle, so joiners see idle users. |
| Key liveness | TTL on `presence:doc` and `cursors:doc` | Every heartbeat (EXPIRE 60) | Expires 60 s after the last write if no node is left. |
| Socket map and throttle timestamp | Node memory only | The node | Lost with the node. Rebuilt from Redis on the next join. |
| Applied rev, held carets, displayed carets, highest seq per connId | Client memory | The client editor | Carets dropped on HistoryGone or on clean close. |

## Rules

- **Per user, not per tab.** The list is built from distinct userIds among live members. Closing one of two tabs changes nothing visible.
- **Revisions.** Each cursor carries the sender's `rev` and `seq`.
  - If `rev` is above `appliedRev`, hold the caret. Draw it when `appliedRev` reaches `rev`.
  - If `rev` is at or below `appliedRev`, map it forward with `transformPosition(pos, rev, appliedRev)`. On HistoryGone, drop the caret until the next update.
  - On every applied revision, re-map the displayed caret from its stored rev to the new `appliedRev`.
- **No backwards jumps.** The receiver keeps the highest seq per connId and discards any message with a lower or equal seq. A held caret is replaced only by a higher seq. The sender's seq only increases, so reordering cannot move a caret back.
- **Messages (new).**
  - Client to server: `cursor {docId, pos, rev, seq}`.
  - Server to client: `presence_snapshot {users, cursors}`, `presence_users {users}`, `cursor {connId, userId, pos, rev, seq}`, `cursor_gone {connId}`.
  - The existing messages (`open`, `op`, `ack`, `remote_op`) are unchanged.

## What happens when things fail

| What goes wrong | What happens | Bounded by |
|---|---|---|
| Tab closes cleanly | Explicit removal and a nudge. Other users see it. | 2 s |
| Nudge is dropped | The next sweep re-reads the members. | 5 s |
| Node crashes, or a connection stops heartbeating | Its entries go stale, then the sweeps remove them. | 35 s after the crash |
| Node crashes and no node with sockets is left | The keys expire. | 60 s after the last write |
| Cursor arrives less than 50 ms after the last accepted one | The node drops it silently. | Per connection |
| Cursor is at a revision the client has not applied | The caret is held and drawn once that revision is applied. | Until applied |
| Old revision history is gone (HistoryGone) | The caret is dropped until the next update. | Next update |
| Cursors arrive out of order | Any message with a lower or equal seq is discarded. | Per connId |
| Redis primary fails over | With async replication, the last few writes can be lost. Heartbeats re-add members. | 10 s |
| Node restarts | Its socket map and throttle timestamps are lost. They are rebuilt on the next join. | Next join |

## Open questions

None block the design. The one accepted risk is the Redis failover row above. Presence heals on its own, so the loss is accepted and stated here.