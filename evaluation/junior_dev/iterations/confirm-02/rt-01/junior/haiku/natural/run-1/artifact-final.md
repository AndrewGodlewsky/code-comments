# Live cursors and presence: sequence design

Presence (who is in a document) and cursors (where each person's caret is) are shared between gateway nodes through Redis, a shared store. Today the presence list is a Postgres table, written on open and close and polled by browsers every 30 s, and users of a crashed node stay listed until a nightly job removes them. This design replaces that polling. A user joins by writing a presence entry and a lease. Each connection refreshes its lease every 10 s, and any node removes expired leases, so a crashed node's users disappear within 40 s. Cursors are never stored durably: each one carries the revision it belongs to and goes away with its connection. The edit path, the document service, Postgres and the load balancer are not changed, and cursors never reach them.

## Terms

- **Gateway node**: one of the six servers that hold browsers' WebSocket connections. A WebSocket is a connection that stays open so the server can push messages. People in one document are usually on different nodes.
- **connId**: a random id for one WebSocket connection. A user with two tabs has two connIds.
- **userId**: the user's id, taken from the session.
- **Redis**: a shared in-memory store that all nodes can reach. The edit path already uses it.
- **Pub/sub**: Redis sends a published message to every node subscribed to that channel at that moment. It stores nothing.
- **Lua script**: a short program that Redis runs as one step. No other Redis command runs in the middle, so its reads and writes act as one atomic step.
- **Redis TIME**: the Redis server's clock. Lease deadlines use it, so the nodes' own clocks do not matter.
- **Key expiry**: Redis deletes a key once its time limit passes.
- **Document keys**: four Redis keys per document, named with its id. The diagram writes them as presence:doc and similar.
  - **presence**: maps connId to user.
  - **leases**: maps connId to its deadline.
  - **cursors**: maps connId to its last cursor.
  - **presence_ver**: a counter (see below).
- **Lease**: a connection's deadline in leases. Each heartbeat moves it 30 s ahead. When it passes, the connection counts as gone.
- **presence_ver**: a per-document counter. It goes up by one for each join or leave that is published, and for nothing else. Each presence event and snapshot carries its value.
- **Presence event**: a join or leave message published on presence:doc.
- **Snapshot**: the full current presence list, stored cursors and presence_ver, sent by a node to one browser.
- **hello**: a message that asks every browser in the document to send its current caret.
- **rev**: the revision number the document service gives each applied edit.
- **appliedRev**: the last revision the editor has applied. It only moves forward. The edit path sets it, and this design only reads it.
- **transformPosition(pos, fromRev, toRev)**: an editor function that moves a character position from an older revision to a newer one. It throws HistoryGone if fromRev is older than the last 500 revisions the editor keeps. The caller then drops the position.
- **seq**: a counter that the sending browser keeps for each connection. It starts when the connection opens and goes up by one for each cursor update.

## Diagram

```mermaid
sequenceDiagram
    autonumber
    participant A as Ann (browser)
    participant N1 as Node 1
    participant R as Redis
    participant N2 as Node 2
    participant B as Ben (browser)
    participant N3 as Node 3
    participant C as Carl (browser)

    Note over B,C: Before the scene: Ben (connId cB) is on Node 2 and Carl (connId cC) is on Node 3. Both are in presence, leases and cursors.

    Note over A,N1: Scene 1: Ann opens the doc on Node 1 while Ben is already in it on Node 2
    A->>N1: open docId (connId cA, userId ann)
    N1->>R: SUBSCRIBE presence:doc and cursor:doc
    N1->>R: Lua sweep, then Lua join cA: HSET presence cA, ZADD leases cA (Redis TIME + 30 s)
    Note over R: If cA is ann's only entry, INCR presence_ver and PUBLISH join ann with the new version. A second tab publishes nothing.
    R-->>N2: presence:doc join ann v
    N2-->>B: presence join ann v
    N1->>R: One atomic read: HGETALL presence and cursors, GET presence_ver
    R-->>N1: presence (cB ben, cC carl), cursors (cB at rev r0, cC at rev r1), version v
    N1-->>A: snapshot v with users ann, ben, carl and stored cursors
    N1->>R: PUBLISH presence:doc hello cA
    R-->>N2: hello cA
    N2-->>B: hello cA
    B->>N2: cursor seq, current rev, current pos, even if idle
    N2->>R: Lua cursor cB: HSET cursors cB if cB has a lease, then PUBLISH cursor:doc
    R-->>N1: cursor cB (fresh rev)
    N1-->>A: cursor cB (fresh rev)
    Note over A: Every browser in the document answers hello. The diagram shows Ben only.

    Note over B,A: Scene 2: Ben moves his caret
    B->>N2: cursor seq 42, rev 812, pos 230 (at most one per 50 ms)
    Note over N2: Dropped silently if Ben's last accepted update was under 50 ms earlier
    N2->>R: Lua cursor cB: HSET cursors cB (seq 42, rev 812, pos 230) if cB has a lease, then PUBLISH cursor:doc
    R-->>N1: cursor cB seq 42 rev 812 pos 230
    N1-->>A: cursor cB seq 42 rev 812 pos 230
    Note over A: Ann applies the receiving rules in step 3

    Note over N1,R: Scene 3: heartbeat and sweep. No caret or presence event is sent.
    loop Every 10 s, for each local connection
        N1->>R: Lua heartbeat cA: ZADD leases XX (Redis TIME + 30 s), then EXPIRE presence, cursors, leases and presence_ver 120 s
    end
    loop Every 10 s, each node with a local socket on the doc
        N2->>R: Lua sweep: remove leases past their deadline (Redis TIME)
        Note over R: For each removed connId, HDEL its presence and cursor. If it was the user's last connection, INCR presence_ver and PUBLISH leave.
    end

    Note over A,N1: Scene 4: Ann closes her tab cleanly
    A->>N1: socket close
    N1->>R: Lua leave cA: ZREM leases, HDEL presence, HDEL cursors
    Note over R: If no presence entry for ann remains, INCR presence_ver and PUBLISH leave ann. Otherwise nothing is published.
    R-->>N2: presence:doc leave ann
    N2-->>B: presence leave ann
    Note over B: Ben's list drops Ann within 2 s. If Ann has another tab, she stays listed.
    N1->>R: UNSUBSCRIBE presence:doc and cursor:doc if no local socket is left on the doc

    Note over N3: Scene 5: Node 3 crashes. It runs no cleanup.
    Note over R: cC stays in leases, presence and cursors until its deadline (last refresh + 30 s) passes
    loop Node 2 sweep tick, every 10 s
        N2->>R: Lua sweep finds cC expired
        Note over R: Lua removes cC (this call wins), HDEL presence and cursor. If it was carl's last connection, INCR presence_ver and PUBLISH leave carl.
    end
    R-->>N2: presence:doc leave carl
    N2-->>A: presence leave carl
    N2-->>B: presence leave carl
    Note over C: Carl's browser reconnects to a live node with a new connId and is listed again
```

Notes on the diagram: each scene shows one kind of event. The rules for what a browser does with each message are in the steps below, not in the diagram notes. Every browser in the document answers hello, not only the ones shown.

## Steps

1. **Join.** Trigger: a browser opens the document. The node subscribes to presence:doc and cursor:doc first, so no event is missed. It then runs the sweep (step 5). The join script writes cA to presence and its lease to leases. In the same script it counts this user's presence entries. If cA is the only one, the script raises presence_ver and publishes join with the new value. If not, it publishes nothing. Because the count and the write are one script, two tabs that join at the same moment still give one join. The node then reads presence, the stored cursors and presence_ver in one atomic read and sends the browser a snapshot. It forwards presence and cursor events to that browser only after the snapshot.
   - An event can arrive that the snapshot already includes. The browser ignores any presence event whose version is at or below the snapshot's version, and applies the rest in order.
   - If the next event skips a number (for example v10 then v12), the browser missed one. It asks its node for a new snapshot.
   - A snapshot always sets the browser's version, even when that is lower, because presence_ver can expire.
   - Every snapshot replaces the browser's list, stored cursors and version, and drops its held and shown carets. The hello that follows brings the carets back.
   - If Redis is down, the join fails and the node closes the socket. The browser reconnects and joins again.
2. **Answer hello.** Trigger: hello. Every browser in the document sends its own cursor with its current rev and position, even if the user is idle. Stored cursors may be old or dropped, so these answers give the current positions. Every snapshot is followed by hello, so a join, a version gap, a rejoin or a resubscribe all bring the carets back.
3. **Move a caret.** Trigger: the local caret moves. The browser sends at most one cursor update per 50 ms, with seq, rev and pos. If the caret moves again inside that window, the browser keeps only the latest position and sends it when the window ends, so the last position is not lost.
   - The node keeps the time of the last accepted update for each connId in its memory. It drops an update silently if it accepted one less than 50 ms earlier. The browser never learns of the drop.
   - Otherwise a Lua script stores the cursor and publishes it, but only if the connId still has a lease. A late update after a leave therefore cannot bring a cursor back.
   - Pub/sub keeps publish order, so a user's join reaches a browser before that user's cursors.

   A receiving browser applies these rules in order:
   - a. Drop the cursor if its connId is not in the browser's list. It is then older than the snapshot or late after a leave.
   - b. Drop the cursor if its seq is not above the last seq shown for that connId. This stops backward jumps, even when messages arrive out of order. A reconnect gets a new connId and counter, so an old seq never blocks it.
   - c. If its rev is above appliedRev, hold it. A newer seq from the same connId replaces the held cursor, so an older one can never be drawn after a newer one. Draw it when that rev is applied, if its seq is still above the last one shown.
   - d. Otherwise move pos with transformPosition(pos, rev, appliedRev). If that throws HistoryGone, drop the cursor until the next update from that connection. If not, draw it.

   Stored cursors in a snapshot go through the same rules.
4. **Heartbeat.** Trigger: every 10 s, for each local connection. The node runs the Lua heartbeat. ZADD with XX moves the lease 30 s ahead. XX means it only updates a lease that already exists. The same script sets presence, cursors, leases and presence_ver to expire in 120 s, so they clear if no node is left alive. If the lease is missing, because it expired during a stall or a Redis outage, the node runs the join steps again for that connection (step 1). That sends a new snapshot and hello, so the browsers' lists and carets are rebuilt.
5. **Sweep.** Trigger: every 10 s on each node with a local socket on the document, and before each join. The Lua sweep removes leases whose deadline has passed, using Redis TIME. For each removed connId, it removes the presence and cursor entries. If that was the user's last connection, it raises presence_ver and publishes leave. The script is atomic, so when two nodes sweep at once, only the call that removes a connId continues. If no node has a socket on the document, nothing sweeps. Nobody is viewing it, and the next join sweeps first.
6. **Clean leave.** Trigger: the socket closes. The node runs the leave script. It removes the lease, presence entry and cursor. If the user has no presence entries left, the script raises presence_ver and publishes leave. Other users see the leave within 2 s. Then the node unsubscribes from presence:doc and cursor:doc if no local socket remains on the document.
7. **Node crash.** A dead node does nothing. Its leases stop being refreshed. Each lease was last refreshed at or before the crash, so it ends at most 30 s after the crash. The next sweep on a surviving node runs every 10 s and removes it, so removal comes at most 40 s after the crash. That is within the 45 s limit. Browsers reconnect to a live node with a new connId. If no node survives, key expiry clears the keys, so nothing stays in Redis for good.

## Where state lives

| State | Where | Written by | Refreshed by | Removed by |
|---|---|---|---|---|
| Presence entry (connId to user) | Redis presence | join | heartbeat | leave, sweep, or key expiry |
| Lease (connId to deadline) | Redis leases | join | heartbeat every 10 s | leave, sweep, or key expiry |
| Cursor (connId to last cursor) | Redis cursors | cursor update | heartbeat | leave, sweep, or key expiry |
| presence_ver | Redis counter | join, leave, sweep, each time one is published | heartbeat | key expiry only |
| Node subscription | node memory | node | none | node unsubscribes when its last local socket leaves |
| Snapshot list | browser memory | node | each new snapshot | each snapshot replaces it; leave and join events change it |
| Held or shown caret | browser memory | receiving browser | next cursor update | leave, a newer seq, or a new snapshot |
| appliedRev | editor | the edit path (unchanged) | the edit path | never removed |

Nothing in this table is written to Postgres or the document service. Key expiry (120 s after the last heartbeat) removes whatever is left when no node is alive.

## When things fail

| What fails | What happens | Recovery |
|---|---|---|
| Redis is down when a browser opens the document | The join fails and the node closes the socket | The browser reconnects and joins again |
| Redis is down, or a live node stalls for more than 30 s | Its leases expire. Other nodes remove its users within 40 s, and its own browsers see the leave too. This is deliberate: a stall over 30 s has to drop the lease | The next heartbeat (within 10 s) finds the lease missing and rejoins, sending a new snapshot and hello. Until then the user is missing from every list |
| A node loses its Redis subscription | It may miss presence events | The Redis client reports the drop and reconnects. The node then resubscribes, sends its local sockets a fresh snapshot and publishes hello |
| A browser misses a presence event (version gap) | Its list may be wrong | It asks its node for a new snapshot, which is followed by hello |
| A cursor update is lost | That caret is stale | The next move or hello fixes it. Cursors are not replayed |
| A stored cursor is older than the kept history (HistoryGone) | Its caret is hidden. A snapshot does not bring it back | It is drawn again from the next update from that connection, such as the answer to hello |
| A held cursor's rev never gets applied | Its caret stays hidden | It is drawn when that rev is applied, unless a newer seq is shown first |
| Node dies and no other node has a socket on the document | Nothing sweeps the stale entries | The next join sweeps first. If nobody joins, key expiry removes them |

## Open questions

- Where the colour for avatars and carets comes from is not decided.
- Carets are keyed by connection, so one user with two tabs may show two carets. It is not decided whether a user should show one caret.
- Which Redis client event reports a lost subscription has not been checked against the gateway code. The resubscribe rule in the failure table depends on it.