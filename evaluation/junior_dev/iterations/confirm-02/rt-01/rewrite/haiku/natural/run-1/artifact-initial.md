# Live cursors and presence: sequence design

Presence and cursors ride on the existing gateway nodes and the existing Redis (pub/sub for fan-out, plus short-lived keys for state). The edit path, the load balancer and Postgres are not touched. The document service is not involved.

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

## Where state lives

| State | Location | Written by | Refreshed or removed by |
|---|---|---|---|
| Presence membership, one member per connection (`userId`, `name`, `colour`, `connId`) | Redis sorted set `presence:doc`, score = last heartbeat time | Node that owns the socket, on join | Heartbeat every 10 s. Removed by clean close (ZREM) or by sweep when score is older than 30 s. |
| User list | Derived, not stored. Distinct `userId` values among live members. | Each receiving node, on read | Recomputed on every nudge and every 5 s sweep. A user is listed while any of their members is live. |
| Last caret per connection | Redis hash `cursors:doc`, field = `connId` | Node, on each accepted cursor update | Removed on clean close, or by sweep when the connId is not a live member. Kept while the user is idle, so joiners see idle users. |
| Liveness of the whole key | TTL on `presence:doc` and `cursors:doc` | Every heartbeat (EXPIRE 60) | Expires 60 s after the last write if no node is left. |
| Socket map, throttle timestamp, highest seq per connId | Node memory only | Node | Lost with the node. Rebuilt from Redis on the next join. |
| Applied rev, held carets, displayed carets | Client memory | Client editor | Carets dropped on HistoryGone or on clean close. |

## Rules the protocol enforces

- **Per user, not per tab.** The list is built from distinct userIds among live members. Closing one of two tabs changes nothing visible.
- **Join gets everything at once.** The node subscribes first, then reads the members and the cursor hash, sends `presence_snapshot`, and only then forwards live frames. Overlap may repeat a message, but the seq rule below makes repeats harmless.
- **Cursor rate.** The node accepts at most one cursor per connection every 50 ms and drops the rest silently. Clients coalesce with a trailing timer so the final position always gets through.
- **Revisions.** Each cursor carries the sender's `rev` and a per-connection `seq`. On receipt:
  - If `rev` is above `appliedRev`, hold the caret. Draw it when `appliedRev` reaches `rev`.
  - If `rev` is at or below `appliedRev`, map it forward with `transformPosition(pos, rev, appliedRev)`. On `HistoryGone`, drop the caret until the next update.
  - On every applied revision, re-map the displayed caret from its stored rev to the new `appliedRev`.
- **No backwards jumps.** The receiver keeps the highest `seq` per connId and discards any message with a lower or equal seq. A held caret is replaced only by a higher seq. Because the sender's seq is strictly increasing, reordering cannot move a caret back.
- **Joiners see idle users.** Every client sends one cursor right after its `open` completes. Its position is then in `cursors:doc`, so users who never move still have a caret for others to see.
- **Ephemeral.** Cursor traffic uses only pub/sub and the `cursors:doc` hash, which expires with the document's presence keys. Nothing goes to the document service or Postgres.

## Protocol messages (new)

- Client to server: `cursor {docId, pos, rev, seq}`.
- Server to client: `presence_snapshot {users, cursors}`, `presence_users {users}`, `cursor {connId, userId, pos, rev, seq}`, `cursor_gone {connId}`.
- Redis pub/sub: `presence:doc` carries nudges (`joined` / `left` / `changed` with connId). `cursor:doc` carries cursor frames. Nudges are only hints. Every node also re-reads on its 5 s sweep, so a dropped nudge costs at most 5 s.

## Requirement check

- Presence list replaces the Postgres polling: yes, all presence state is in Redis and pushed live.
- Full list on join, then live changes: yes, snapshot then nudges.
- Cursors on join, including idle users: yes, via `cursors:doc`.
- 50 ms per connection, silent drop: yes, enforced on the node.
- Ephemeral, never in Postgres: yes.
- Revision hold, transform forward, no backwards jumps: yes, via `rev` and `seq`.
- Clean leave within 2 s: explicit ZREM and nudge, both immediate.
- Node crash gone within 45 s: removal at most 35 s after the crash (30 s stale window plus 5 s sweep). Nothing is left for good: keys expire 60 s after the last write.

## Open points for the implementer

- Redis failover: with async replication, a primary failover can lose the last few writes. Presence is self-healing (heartbeats re-add members within 10 s), so this is acceptable, but it should be stated.
- Sweeps from several nodes at once are idempotent, so no leader election is needed.
- The member string must be stored exactly as written, because ZREM needs an exact match. The node that created it keeps it for the connection's life.