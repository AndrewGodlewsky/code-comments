# Live cursors and presence: sequence

## Decisions

- **All presence and cursor state lives in the Redis we already run.** Nothing new is added, and the edit path, the document service and the load balancer stay as they are. Each doc gets two keys and one channel, and every change goes through a short Lua script so that it is atomic.
  - `pres:conns:{doc}` is a ZSET. Each member is `userId/connId` and its score is the time of that connection's last heartbeat, taken from Redis `TIME` so that clocks on different nodes don't matter.
  - `pres:cur:{doc}` is a HASH. Each field is a `connId` and its value is `{userId, rev, pos, seq}`, the last accepted cursor for that connection.
  - `pres:{doc}` is a pub/sub channel. It carries the `presence`, `cursor` and `cursor_gone` events, in the order Redis ran the scripts.
- **Presence is stored per connection and published per user.** A script publishes `presence {userId, present: true}` only when that user had no other member yet. It publishes `present: false` only when the user's last member is removed. Events state the absolute state, not a delta, so applying one twice does nothing.
- **Carets are keyed by `connId` and coloured by `userId`.** A user with two tabs has two carets in the same colour. A client ignores carets that carry its own `userId`.
- **`seq` is set by the gateway node.** It increases for each accepted cursor on a connection. Only one node ever owns a connection, so there is a single writer. Receivers use `seq` to drop updates that are stale, duplicated or out of order.
- **A node subscribes to `pres:{doc}` on the same terms as `ops:{doc}`.** It subscribes while it has at least one local socket on the doc, and it never echoes a cursor back to the connection that sent it.

```mermaid
sequenceDiagram
    autonumber
    participant A as Alice tab (browser)
    participant N1 as Gateway node 1
    participant R as Redis
    participant DS as Document service
    participant N2 as Gateway node 2
    participant B as Bob tab (browser)

    Note over N2,B: Before: Bob (conn b1) is in the doc via N2.<br/>N2 memory: localSockets[doc] = {b1}, Conn b1 = {lastCursorAt, seq 7, lastCursor}.<br/>N2 is subscribed to ops:{doc} and pres:{doc}.
    Note over R: Per doc, both keys carry TTL 60 s, refreshed by every join and heartbeat<br/>pres:conns:{doc} ZSET, member userId/connId, score = last heartbeat (Redis TIME)<br/>pres:cur:{doc} HASH, field connId = {userId, rev, pos, seq}<br/>pres:{doc} pub/sub channel, stores nothing

    Note over A,B: JOIN. Alice lands on N1, which has no other socket on this doc
    A->>N1: open {docId}
    N1->>N1: localSockets[doc] add a1, Conn a1 = {lastCursorAt 0, seq 0}
    N1->>R: SUBSCRIBE ops:{doc} pres:{doc}
    R-->>N1: subscribed. From now on, pres events for a1 are queued, not forwarded
    N1->>R: EVAL join(doc, alice/a1)
    Note over R: atomic: ZADD score = TIME, EXPIRE both keys 60 s,<br/>PUBLISH alice present only if no other alice member existed,<br/>return all members and HGETALL pres:cur:{doc}
    R--)N2: pres:{doc} presence {alice, present}
    N2--)B: presence {alice, present}
    R-->>N1: members [alice/a1, bob/b1], cursors {b1: rev 41, pos 120, seq 7}
    N1-->>A: presence_snapshot {users [alice, bob], cursors [b1 rev 41 pos 120 seq 7]}
    N1-->>A: then the queued pres events, then live forwarding
    Note over A: Document loaded as today, appliedRev 41.<br/>Avatars = distinct userIds. b1 is at rev 41, already applied:<br/>draw at transformPosition(120, 41, 41), lastSeq[b1] = 7.<br/>A queued event for b1 with seq 7 or lower is dropped.
    A->>N1: cursor {docId, rev 41, pos 0}, sent once right after load
    N1->>R: EVAL cursor(doc, a1, {alice, 41, 0, seq 1})
    R--)N2: pres:{doc} cursor {a1, alice, rev 41, pos 0, seq 1}
    N2--)B: cursor {a1 ...}. Bob draws Alice's caret even if she never moves

    Note over A,B: CURSOR MOVE. Bob types one character and his caret moves
    B->>N2: op {docId, baseRev 41, ops}
    N2->>DS: forward over HTTP (edit path unchanged)
    DS->>R: append to Postgres, PUBLISH ops:{doc} {rev 42, ops}
    R--)N2: ops:{doc} rev 42
    N2-->>B: ack {rev 42}. Bob appliedRev = 42
    B->>N2: cursor {docId, rev 42, pos 121}
    N2->>N2: at least 50 ms since the last accepted cursor on b1: accept, seq 8, lastCursorAt = now
    N2->>R: EVAL cursor(doc, b1, {bob, 42, 121, 8})
    Note over R: only if ZSCORE bob/b1 exists:<br/>HSET pres:cur:{doc} b1 if seq is higher than the stored one, PUBLISH pres:{doc}.<br/>Never touches the document service or Postgres.
    R--)N2: pres:{doc} cursor b1 seq 8 (N2 skips b1, no echo)
    R--)N1: pres:{doc} cursor {b1, bob, rev 42, pos 121, seq 8}
    N1--)A: cursor {b1, bob, rev 42, pos 121, seq 8}
    Note over A: seq 8 is newer than 7. rev 42 is ahead of appliedRev 41:<br/>keep it as pending[b1] and leave the shown caret where it is
    R--)N1: ops:{doc} rev 42 (the two channels are not ordered, so this can arrive second)
    N1--)A: remote_op {rev 42, ops}
    Note over A: apply, appliedRev = 42. Move shown carets forward from 41 to 42.<br/>pending[b1] is now applied: draw at transformPosition(121, 42, 42), lastSeq[b1] = 8
    B->>N2: cursor {docId, rev 42, pos 122}, only 20 ms later (misbehaving client)
    N2->>N2: under 50 ms since the last accepted cursor: drop silently, no seq used

    Note over A,B: HEARTBEAT. Timers on every node and every client
    loop every 10 s
        N1->>R: EVAL heartbeat(doc, [alice/a1])
        N2->>R: EVAL heartbeat(doc, [bob/b1])
        Note over R: each listed member: ZADD score = TIME. If it was missing (evicted<br/>during a long pause), re-add it and PUBLISH present. The node then re-sends its last cursor.<br/>EXPIRE both keys 60 s.<br/>Sweep: every member with score older than TIME minus 30 s is removed like a leave.
        N1->>A: WebSocket ping (unchanged. No pong within 20 s: close the socket and run leave)
        A-->>N1: pong
        opt client timer: appliedRev moved since the last cursor sent
            B->>N2: cursor {docId, rev 57, pos 140}, same caret at the current revision
        end
    end

    Note over A,B: CLEAN LEAVE. Alice closes her tab
    A->>N1: WebSocket close frame
    N1->>N1: localSockets[doc] remove a1. It was the last local socket on this doc
    N1->>R: EVAL leave(doc, alice/a1)
    Note over R: if ZREM alice/a1 removed something: HDEL pres:cur:{doc} a1,<br/>PUBLISH cursor_gone a1, and if no alice member is left PUBLISH alice absent.<br/>If the ZSET is now empty, DEL both keys.
    R--)N2: cursor_gone {a1}, presence {alice, absent}
    N2--)B: cursor_gone {a1}, presence {alice, absent}
    N1->>R: UNSUBSCRIBE ops:{doc} pres:{doc}
    Note over B: Alice's caret and avatar are gone within milliseconds, well inside 2 s.<br/>If she still had a second tab open, only cursor_gone a1 would be sent and she would stay listed.

    Note over A,N1: Later Alice reopens the doc and lands on N1 again as conn a2. Join runs as above.

    Note over A,B: NODE CRASH. N2 is killed just after its heartbeat at time T, and no cleanup runs
    Note over N2: dead. bob/b1 and its cursor stay in Redis with score T
    B--xN2: socket lost
    loop N1 heartbeats before T + 30 s
        N1->>R: EVAL heartbeat(doc, [alice/a2])
        Note over R: bob/b1 is less than 30 s old, so it is kept
    end
    N1->>R: EVAL heartbeat(doc, [alice/a2]), first run after T + 30 s, by T + 40 s at the latest
    Note over R: sweep: bob/b1 is stale. ZREM bob/b1, HDEL b1,<br/>PUBLISH cursor_gone b1, and with no other bob member PUBLISH bob absent
    R--)N1: cursor_gone {b1}, presence {bob, absent}
    N1--)A: cursor_gone {b1}, presence {bob, absent}
    Note over A: Bob's caret and avatar disappear 30 to 40 s after the crash, under 45 s.<br/>If Bob's browser reconnects first (as b3 through the load balancer), he stays listed<br/>and only cursor_gone b1 is sent.
    Note over R: If no node with sockets on this doc survives, nobody sweeps and nobody is watching.<br/>Both keys then expire 60 s after the last heartbeat, so nothing is left in Redis for good.
```

## Where each piece of state lives

| State | Where | Written by | Refreshed by | Removed by |
|---|---|---|---|---|
| `localSockets`, `Conn {lastCursorAt, seq, lastCursor}` | Gateway memory | open | – | socket close or ping timeout; lost when the node dies |
| Connection presence `userId/connId` | Redis ZSET `pres:conns:{doc}` | `join` script | `heartbeat` script every 10 s (score = Redis `TIME`) | `leave` on close; a sweep once older than 30 s; `DEL` when empty; key TTL 60 s |
| Last cursor per connection | Redis HASH `pres:cur:{doc}` | `cursor` script, only for a member that is still present, and only when `seq` is higher | each new cursor; the client re-sends every 10 s once its `appliedRev` has moved; key TTL refreshed by heartbeat | same script as the presence member (`HDEL`); key TTL 60 s |
| Live events | Redis channel `pres:{doc}` | the same scripts, atomic with the state change | – | not stored |
| Avatars, shown carets, `pending`, `lastSeq` | Browser memory | snapshot plus events | – | `presence absent`, `cursor_gone`, page close |

The Postgres presence table, the 30 s client polling and the nightly cleanup job are all removed.

## Join without a gap

1. The node subscribes to `pres:{doc}` before it reads the snapshot. If it is already subscribed for another local socket, nothing changes.
2. It queues events for the new connection until the snapshot has been sent.
3. It then sends the queued events, in order.

The snapshot is taken by the same script that registers the connection, so it is consistent with that registration. Every event states an absolute state and the channel delivers in the order Redis ran the scripts, so the last event the client gets for each user or connection always matches the current state.

A cursor queued from before the snapshot is either dropped by `seq`, or followed by its `cursor_gone` later in the same queue.

## Receiver rules (client)

```ts
// New messages
type SendCursor  = { t: "cursor"; docId: string; rev: number; pos: number };          // client -> server
type CursorState = { connId: string; userId: string; rev: number; pos: number; seq: number };
type PresenceSnapshot = { t: "presence_snapshot"; users: string[]; cursors: CursorState[] };
type Presence    = { t: "presence"; userId: string; present: boolean };
type RemoteCursor = { t: "cursor" } & CursorState;
type CursorGone  = { t: "cursor_gone"; connId: string };

function onCursor(c: CursorState) {            // snapshot entries go through this as well
  if (c.userId === myUserId) return;
  if (c.seq <= (lastSeq.get(c.connId) ?? 0)) return;   // older or duplicate: never jump back
  lastSeq.set(c.connId, c.seq);
  if (c.rev > appliedRev) { pending.set(c.connId, c); return; }  // not applied yet: hold it
  pending.delete(c.connId);
  draw(c.connId, c.pos, c.rev);
}
function draw(connId: string, pos: number, rev: number) {
  try { shown.set(connId, { pos: transformPosition(pos, rev, appliedRev), rev: appliedRev }); }
  catch { /* HistoryGone: drop this position, keep whatever caret is already shown */ }
}
function onApplied() {                          // after each ack or remote_op moves appliedRev
  for (const [id, s] of shown) draw(id, s.pos, s.rev);
  for (const [id, c] of pending) if (c.rev <= appliedRev) { pending.delete(id); draw(id, c.pos, c.rev); }
}
function onCursorGone(id: string) { shown.delete(id); pending.delete(id); lastSeq.delete(id); }
```

- Every call keeps to the `transformPosition` contract: `fromRev <= toRev = appliedRev`, and a position is dropped when the call throws.
- A sender's `appliedRev` only moves forward, so a higher `seq` never carries a lower `rev`. Holding only the newest pending update therefore never shows an older position.
- An idle sender re-sends its caret whenever its `appliedRev` has moved, checked every 10 s. This keeps the stored cursors close to the head revision, so a joiner's `transformPosition` doesn't hit `HistoryGone` and idle carets still show up on join.
- Carets are kept at `appliedRev`. If the editor has local ops that are not acknowledged yet, it maps the drawn caret through them for display only.

## Sending and rate

- The client throttles to one cursor every 60 ms and always sends the last position (trailing edge).
- Once the caret stops, the client sends the final position once more after 250 ms. If network jitter made the server drop the last throttled update, this repeat restores it.
- The server checks 50 ms per connection, on arrival. It drops faster updates silently and gives them no `seq`.

## Timing budget

| Event | Bound |
|---|---|
| Clean close | Close frame, `leave` script, publish, forward: milliseconds, well under 2 s |
| Connection lost, node alive | Existing ping/pong closes the socket within 30 s, then `leave` runs |
| Node crash | The member is stale 30 s after its last heartbeat. A node still on the doc sweeps every 10 s, so removal is 30 to 40 s after the crash, plus under 1 s of delivery: under 45 s |
| Everything about a doc gone | `DEL` when the last member leaves. Otherwise the key TTL is 60 s after the last heartbeat or join |

- Sweeps by several nodes are safe. A script publishes only when its `ZREM` actually removed the member, so a `leave` that runs after a sweep, or a second sweep, publishes nothing.
- A live node can be paused long enough to be swept, for example by a long GC pause. Its next heartbeat or cursor finds the member missing. It re-adds the member, which publishes `present`, and then re-sends the last cursor with a new `seq`.
- On a Redis failover, writes that had not reached the replica are restored by the next heartbeat (within 10 s) and by the next cursor.
