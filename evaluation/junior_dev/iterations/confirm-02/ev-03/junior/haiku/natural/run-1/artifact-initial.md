## Chat message fan-out: design

### Diagram

```
SEND PATH (synchronous; the sender's ack comes from step 3 and never waits on fan-out)

 Sender client
     |  1. send {client_msg_id, conv_id, body}             (WebSocket)
     v
 Gateway node  --2. one DB transaction-->  MESSAGE STORE (existing conversation DB)
     ^                                      messages, conv_seq, outbox, pending
     |  3. ack {msg_id, seq}  or  error (on failed write)
     |
 Sender client


FAN-OUT PATH (asynchronous, after commit)

 MESSAGE STORE outbox
     |  4. relay polls unpublished rows, publishes to fan-out topic
     |     (key = conv_id), marks row published after broker ack
     v
 FAN-OUT TOPIC (durable, at-least-once)
     |  consume
     v
 FAN-OUT WORKER
     |  5. load members (<= 199, sender excluded)
     |     batch INSERT pending (user_id, msg_id) ON CONFLICT DO NOTHING
     |  6. read PRESENCE for each recipient
     |
     +--- online ----------------------------------------+
     |  7a. hint to recipient's gateway node             |
     |      gateway -> recipient WS -> client ack        |
     |      gateway: 9. DELETE pending row              |
     |                                                   |
     +--- offline or presence unknown -----------------+ |
     |  7b. push now (best effort, no retry)           | |
     |                                                 | |
     +--- 8. delayed job at hint time + 5 s ----------+-+
             if pending row still exists and push_sent_at IS NULL:
             set push_sent_at, send push (best effort, no retry)


RECONNECT PATH

 Recipient client reconnects to any gateway node
     |  10. gateway SETs PRESENCE (user -> node, TTL 30 s) BEFORE step 11
     |  11. gateway SELECT pending WHERE user_id = ?
     |       ORDER BY conv_id, seq   (paged)
     |  client drops duplicates by msg_id, orders each conversation by seq
     |  client ack {msg_id} -> gateway DELETE pending row (idempotent)
```

### Where state lives

- **Message id, sequence number, body, sender, client message id.** Message Store `messages` table. The unique key on `(sender, client_msg_id)` is what makes a retry return the existing row.
- **Per-conversation sequence counter.** Message Store `conv_seq` table. The send transaction increments it with `UPDATE ... RETURNING`. The row lock held until commit means commit order matches sequence order, and a rollback leaves no gap.
- **Fan-out intent.** Message Store `outbox` table, written in the same transaction as the message. A message is either committed with its outbox row or not at all, which is why a failed write fans out to nobody.
- **Per-recipient pending state.** Message Store `pending` table, keyed `(user_id, msg_id)`. It holds `conv_id`, `seq`, `push_sent_at` and `expires_at = created_at + 30 days`. This table is the source of truth for "not yet delivered". A row is deleted only when the client acks it.
- **Membership.** The existing conversation membership table, read-only here. The fan-out uses the membership snapshot taken when it runs.
- **Presence.** A key-value store with TTL, one key per user holding gateway node id and connection id, refreshed by each 10 s heartbeat with a 30 s TTL. It is not durable. Losing it only degrades routing, and reconnects rebuild it.
- **Live hints.** In memory on the gateway, and not durable. A lost hint is covered by the step 8 push check and by the reconnect sync.
- **Fan-out topic.** The message broker, durable, at-least-once. Its retention must exceed worst-case fan-out lag.
- **Client state.** A set of seen message ids for dedupe, and the highest seq per conversation to detect gaps.

### Failure handling

- **Message Store write fails.** The sender gets an error. Nothing commits, so no outbox row exists and nothing fans out. The client retries with the same `client_msg_id`, and the unique key ensures at most one row.
- **Commit succeeds but the ack is lost.** The retry hits the conflict branch, returns the existing `msg_id` and `seq`, and writes no second outbox row.
- **Crash after commit, before relay.** The outbox row stays unpublished. The relay publishes it later, so every recipient still eventually gets the message.
- **Relay crashes after publish, before marking published.** The message is published twice. The fan-out is idempotent (`ON CONFLICT DO NOTHING` on pending, and `push_sent_at` guards pushes), so duplicates change nothing.
- **Fan-out worker crashes.** The topic message is not acked, so it is redelivered. Step 5 and step 8 are safe to repeat.
- **Gateway node crashes.** Its live hints and WebSockets are lost. Presence expires within 30 s. Pending rows remain, so the step 8 push check still fires for unacked recipients, and the client reconnects to another node and syncs.
- **Recipient is online but the hint is lost or the ack takes over 5 s.** The row is still pending when the step 8 check runs, so the recipient gets a push. The duplicate later is dropped by message id.
- **Presence store unavailable.** Fan-out cannot tell who is online. It still writes pending rows, sends no live hints, and sends pushes only through the step 8 check (5 s after no ack), so over-notification is possible during the outage. Accepted.
- **Race between fan-out and reconnect.** Fan-out writes pending before reading presence. A connect writes presence before reading pending. Whichever runs second sees the other's write, so a message cannot be stuck pending while the user is online and syncing. This needs a store with read-after-write consistency for these two keys.
- **Push provider fails or times out.** The failure is logged. Push is never retried. `push_sent_at` is set regardless, and the pending row is untouched, so storage is never affected.
- **Recipient offline for more than 30 days.** Pending rows expire and a sweeper deletes them. The messages stay in `messages`, and the client can backfill through the history API when it sees a seq gap.
- **Client reconnects during a live delivery.** Live and sync deliveries may interleave. The client dedupes by message id and orders each conversation by seq, so the on-screen result is correct even when arrival order is not.

### Open boundaries

- Live delivery order is not guaranteed across an ack timeout. Only the reconnect sync is guaranteed to be in sequence order.
- A member added or removed while fan-out runs is handled by the membership snapshot. A member added after the snapshot will not get that message through fan-out and must backfill from history.
- Each message costs up to 199 pending inserts and up to 199 delayed checks. These should be batched. Per-conversation throughput is capped by the `conv_seq` row lock, which is acceptable at 200 members.
- Pending and messages share the Message Store for transactional simplicity. Moving pending to its own store is possible but adds a cross-store consistency problem the design does not cover.
- Typing indicators, read receipts, edits and deletes are out of scope.