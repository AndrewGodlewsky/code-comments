## Chat message fan-out: design

### Summary

Today a client sees a new message only when it reloads the conversation history. This design adds live delivery. A message is written once, with its sequence number and an outbox row, in one database transaction, and the sender is acked from that write alone. A separate worker then gives the message to each recipient, as a live hint if they are connected or as a push if not, and a pending row keeps it until that recipient acks it. Fan-out runs after the ack so that no recipient can slow the sender, and every step can be repeated safely after a crash, so a client that reconnects catches up in sequence order.

### Terms

**Stores and tables** (all in the Message Store, the existing conversation database, unless marked otherwise)

- **messages**: one row per message, with msg_id, seq, body, sender and client_msg_id. The pair (sender, client_msg_id) is unique, so a retry cannot make a second row.
- **conv_seq**: one counter row per conversation. Each new message takes its seq from it.
- **outbox**: committed messages waiting to be published to the topic. Each row is written in the same transaction as its message.
- **pending**: one row per (user_id, msg_id) for each recipient who has not yet acked a message. It holds conv_id, seq, hinted_at, push_sent_at, created_at and expires_at (created_at + 30 days). It is written by the fan-out worker at step 5, not by the send transaction. It is the source of truth for "not yet delivered". A row is deleted when the client acks it or when it expires.
- **membership**: the existing table of who is in each conversation. This design only reads it.
- **Presence**: not in the Message Store. A key-value store (one value per key) with a TTL (an entry that deletes itself unless it is refreshed in time). It has one key per user, holding the gateway node address and connection id. It is not durable. Losing it only degrades routing, and reconnects rebuild it.

**Identifiers and fields**

- **client_msg_id**: an id the client makes before it sends a message. It reuses the same id on every retry.
- **msg_id**: the unique id of a message. The database assigns it when the row is inserted.
- **seq**: the message's position in its conversation, taken from conv_seq.
- **hinted_at**: the time the fan-out worker first tried a live hint for a pending row. It is set once.
- **push_sent_at**: the time a push was claimed for a pending row. It is set once, so a row gets at most one push.

**Processes and delivery**

- **Gateway node**: a server that holds clients' WebSocket connections. A WebSocket is a connection that stays open, so the server can send to the client at any time. Each client connects to one of several gateway nodes.
- **Heartbeat**: a message the client sends every 10 seconds to show it is still connected. Each heartbeat refreshes the user's presence entry, which has a 30-second TTL. A user with no heartbeat for 30 seconds counts as offline.
- **Relay**: a separate worker process that copies outbox rows to the topic. Several copies may run.
- **Topic**: a durable queue in the message broker (the service that carries messages between processes). An item stays until a consumer acks it, so an unacked item is delivered again. This design calls it the fan-out topic. Its retention must exceed the worst-case fan-out lag.
- **Fan-out worker**: a process that reads the topic and does steps 5 to 8.
- **Hint**: a live message from the fan-out worker, through the gateway, to a connected client. The worker sends it to the gateway node whose address is in presence. The gateway passes it over the recipient's WebSocket if that node still has an open socket for the connection id. It carries the full message (msg_id, conv_id, seq, sender and body), so the client never fetches the body separately. It is kept only in memory on the gateway and is not durable. A lost hint is covered by the sweeper and by the reconnect sync.
- **Ack**: a message a client sends to confirm it has received something. The client acks each message it receives, live or during sync.
- **Sweeper**: a timed job in each fan-out worker. Every second it sends pushes for pending rows whose 5-second window has passed, and it deletes expired rows.
- **Push**: a mobile push notification, sent through the push provider (the outside service that delivers notifications to phones). Push is best effort: it is sent once and never retried.
- **Sync**: the reconnect delivery of a user's pending rows.
- **Client state**: the msg_ids the client has seen, and the highest seq it has per conversation.
- **Gap**: a seq the client has neither received nor sent itself. The sender gets no pending row for its own message, so the client knows its own seqs from the acks it received.

**Database and delivery words**

- **Row lock**: a lock that makes other writers wait on a row until the transaction ends.
- **ON CONFLICT DO NOTHING**: an insert that is skipped when a row with the same key already exists, so repeating it changes nothing.
- **FOR UPDATE SKIP LOCKED**: a select that skips rows another process has already locked, so two relay copies never take the same row.
- **Idempotent**: safe to repeat, with the same result as one run.
- **At-least-once**: every message is delivered one or more times, so duplicates are possible.
- **Dedupe**: drop a message whose msg_id the client has already seen.
- **Read-after-write consistency**: once a write finishes, a later read sees it.

### Diagram

```
SEND PATH (synchronous; the sender's ack depends only on the database write)

 Sender client
     |  1. send {client_msg_id, conv_id, body}          (WebSocket)
     v
 Gateway node --2. one DB transaction--> MESSAGE STORE (existing conversation DB)
     ^                                    messages, conv_seq, outbox
     |  3. ack {msg_id, seq}, or error if the write failed
 Sender client


FAN-OUT PATH (asynchronous, after commit)

 MESSAGE STORE outbox
     |  4. relay (one or more copies) takes unpublished rows with
     |     FOR UPDATE SKIP LOCKED, publishes them to FAN-OUT TOPIC
     |     (key = conv_id), marks each row published after the broker ack
     v
 FAN-OUT TOPIC (durable, at-least-once)
     |  consume
     v
 FAN-OUT WORKER
     |  5. load members (<= 199, sender excluded)
     |     batch INSERT pending (user_id, msg_id, conv_id, seq)
     |     ON CONFLICT DO NOTHING
     |  6. read PRESENCE for each recipient
     |
     +-- 7a. presence found (online)
     |       set pending.hinted_at = now if it is NULL, then send a hint with the full
     |       message to the recipient's gateway node
     |       gateway -> recipient WebSocket -> client ack {msg_id}
     |       (step 9 deletes the pending row)
     |
     +-- 7b. no presence (offline)
     |       set pending.push_sent_at = now only if it is NULL, then send push
     |       (best effort, no retry)
     |
     +-- 7c. presence store unavailable, or the hint send failed after 7a
             set pending.hinted_at = now if it is NULL, send nothing (step 8 pushes later)

     8. SWEEPER (every 1 s, in each fan-out worker, over all recipients)
           pending rows with hinted_at < now - 5 s and push_sent_at IS NULL
           claim each with UPDATE ... SET push_sent_at = now WHERE push_sent_at IS NULL
           the copy that claims a row sends its push (best effort, no retry)
           also deletes pending rows past expires_at


RECONNECT PATH

 Recipient client connects to any gateway node
     |  10. gateway writes PRESENCE (user -> node address, connection id,
     |      TTL 30 s) BEFORE step 11. Heartbeats every 10 s refresh the TTL.
     |  11. gateway reads the user's pending rows JOIN messages,
     |      ORDER BY conv_id, seq, in pages; each page carries message bodies;
     |      then a sync-complete frame
     |  client drops duplicates by msg_id, orders each conversation by seq
     |  9. client ack {msg_id} -> gateway DELETE pending row (idempotent)
```

### Steps

1. **Send.** Trigger: the user presses send. The client sends {client_msg_id, conv_id, body} over its WebSocket. It keeps the same client_msg_id and retries until it gets an ack.

2. **Write.** Trigger: the gateway receives a send. It runs one transaction on the Message Store. The transaction does not write pending rows.
   - It inserts into messages with ON CONFLICT (sender, client_msg_id) DO NOTHING. The database assigns msg_id.
   - If the insert succeeded, the same transaction increments conv_seq with UPDATE ... RETURNING to get seq, inserts the outbox row, and commits.
   - If the insert conflicted, the transaction reads the existing row and writes nothing else.

   The insert runs first, so a retry never takes a sequence number. The conv_seq row lock is taken only at the increment and is held until commit. A second sender in the same conversation can run its insert, but it waits at the increment until the first transaction commits or rolls back. This makes commit order match seq order, and a rollback leaves no gap.
   If it goes wrong: if the write fails, nothing commits, so there is no outbox row and nothing fans out. The client retries with the same client_msg_id, and the unique key keeps at most one row. If the commit succeeds but the ack is lost, the retry hits the conflict branch, returns the existing msg_id and seq, and writes no second outbox row.

3. **Ack the sender.** Trigger: step 2 commits. The gateway sends the sender {msg_id, seq}. It never waits for recipients. If step 2 fails, the sender gets an error instead.

4. **Relay.** Trigger: a timer every 500 ms. The relay is a separate worker process, not part of the gateway, so it can scale on its own. Each copy selects unpublished outbox rows with FOR UPDATE SKIP LOCKED, so no two copies take the same row. It publishes them to the fan-out topic with key conv_id, waits for the broker's ack, then marks the rows published and commits. Keying by conv_id puts one conversation's rows in one partition, so a single consumer sees them in publish order. The file does not guarantee order, though. Several relays, and retries after a failed publish, can publish out of order, so live delivery order is not guaranteed. Only the reconnect sync is in sequence order.
   If it goes wrong: outbox rows keep their data until they are published.
   - If the broker or relay is unavailable, the rows stay unpublished and are retried on the next tick.
   - If the commit happened but the relay has not run yet, the row stays unpublished. A later tick publishes it, so every recipient still gets the message.
   - If the relay publishes and then crashes before marking the rows published, the message is published twice. Fan-out is idempotent, because ON CONFLICT DO NOTHING covers pending and push_sent_at guards pushes, so duplicates change nothing.

5. **Pending rows.** Trigger: a message arrives on the topic. The worker reads the conversation's membership now. A conversation has at most 200 members, so there are at most 199 recipients, because the sender is left out. The worker writes one pending row per recipient in one batch insert (user_id, msg_id, conv_id, seq), with ON CONFLICT DO NOTHING, so rows that already exist are left alone. This membership read is the snapshot that the rest of the fan-out uses.
   If it goes wrong: if the worker crashes before it acks the topic message, the broker redelivers the message. Steps 5 to 8 are safe to repeat.

6. **Presence check.** Trigger: step 5 finishes. For each recipient, the worker reads presence. Presence returns the node address and connection id, or nothing.
   If it goes wrong: if the presence store is unavailable, the worker takes branch 7c for every recipient. Pending rows are still written, but no hints go out. The sweeper pushes every recipient 5 seconds after the write, so over-notification is possible during the outage. This is accepted.

7. **Delivery.** Trigger: step 6 gives each recipient a result. There are three branches, shown in the diagram.
   - **7a, online (presence found).** If hinted_at is NULL, set it to now. Then the worker sends a hint with the full message to the node address from presence, through an internal call to that node. If the node has an open WebSocket for the connection id, it passes the hint over it. The client acks {msg_id}, and step 9 deletes the pending row. If the node has no open socket for that connection id, it reports no connection, the hint counts as failed, and branch 7c applies.
   - **7b, offline (no presence).** If push_sent_at is NULL, set it to now, then send a push. The sweeper skips rows with push_sent_at set, so an offline recipient gets one push, not two.
   - **7c, presence unavailable, or the hint failed after 7a.** If hinted_at is NULL, set it to now and send nothing. The sweeper pushes later.

   A hint is never retried. hinted_at is set once, by the first hint attempt, so a failed hint after 7a does not restart the 5-second window. Step 8 is the only path that retries, and it sends only one push per row.
   If it goes wrong:
   - Presence points to a node that no longer has the connection. The node reports no connection, so no hint reaches the client. The sweeper pushes 5 seconds later, and the stale entry expires within 30 seconds.
   - The gateway node crashes. Its hints and WebSockets are lost, and its presence expires within 30 seconds. Pending rows remain, so the sweeper pushes unacked recipients 5 seconds after their hint time. Clients reconnect to another node and sync.
   - The fan-out worker crashes after it sets push_sent_at but before the push is sent. The push is lost. This is accepted, because push is best effort and never retried. On redelivery, push_sent_at is already set, so no second push is sent.
   - The fan-out worker crashes after it sets hinted_at but before the hint is sent. On redelivery, hinted_at keeps its first value, the worker sends the hint again if the recipient is still online, and the sweeper still pushes 5 seconds after the first hint time if the row is unacked.
   - The push provider fails or times out. The failure is logged and never retried. push_sent_at is set anyway, and the pending row is untouched, so storage is not affected.

8. **Sweeper.** Trigger: a timer every 1 second, in every fan-out worker, over all pending rows. It needs no job per recipient, so nothing is created or cancelled. It selects pending rows whose hinted_at is more than 5 seconds old and whose push_sent_at is NULL. It claims each row with UPDATE ... SET push_sent_at = now WHERE push_sent_at IS NULL. The copy that wins the claim sends the push, best effort, with no retry. The sweeper also deletes pending rows past expires_at. A row the client acked in time was already deleted at step 9, so it is never pushed. The 5-second window catches both lost hints and slow acks, because the brief treats an ack that takes over 5 seconds as offline.
   A push is sent only for a row that still exists when the claim runs. A recipient who acks in time is never pushed. A recipient who got a push in step 7b and later syncs still gets the message through sync, and no second push is sent, because push_sent_at is already set.
   If it goes wrong:
   - A hint is lost, or the ack takes over 5 seconds. The row is still pending, so the recipient gets a push. A later duplicate is dropped by msg_id.
   - Every fan-out worker is down. The sweep resumes when one restarts.
   - The recipient stays offline for more than 30 days. The row expires and the sweeper deletes it. The message stays in messages, and the client backfills through the history API when it sees a gap.

9. **Client ack.** Trigger: the client acks a msg_id, live or during sync. The ack goes to whichever gateway node the client is connected to, not necessarily the node that sent the hint. The gateway knows the user from the WebSocket and deletes the pending row for (user_id, msg_id). Any node can do this, because pending lives in the Message Store. Repeating an ack does nothing.

10. **Reconnect presence.** Trigger: a client connects to any gateway node. The gateway writes presence (user to node address and connection id, TTL 30 seconds) before it reads pending rows. Heartbeats every 10 seconds refresh the TTL. So a message written in the meantime is either seen by step 11's read, or hinted to this node.
    Steps 5 and 6 write pending before they read presence. This step writes presence before step 11 reads pending. Whichever runs second sees the other's write. A message therefore cannot stay pending while the user is online and syncing. This needs read-after-write consistency for these two keys.

11. **Sync.** Trigger: step 10 is done. The gateway reads the user's pending rows joined with messages, ordered by conv_id and seq, in pages of 100. Each page carries the message bodies. After the last page it sends a sync-complete frame, which tells the client the sync has finished. The client drops duplicates by msg_id and orders each conversation by seq. It acks each message (step 9), which deletes that row. Rows the client has not acked stay pending and come again on the next connect. The client may get a message both live and in sync, so dedupe handles that.
    On a gap, the client fetches the missing seqs from the existing conversation history API. This is how a client recovers messages that expired from pending.
    If it goes wrong:
    - The client drops during sync. Unacked rows stay pending and are sent again on the next connect.
    - The client reconnects during live delivery. Live and sync deliveries may interleave. The client dedupes by msg_id and orders by seq, so the result on screen is correct even when arrival order is not.

### Open questions

- Multiple devices per user are out of scope. The brief assumes one device, so a second connect overwrites presence. The first socket gets no hints until its client syncs, and the sender's other devices get no copy.
- The internal call from the fan-out worker to a gateway node (protocol and address format) is not chosen yet. Step 7a fixes only the behaviour: a hint either passes or counts as failed.
- Live delivery order is not guaranteed across an ack timeout or across relays. Only the reconnect sync is in sequence order.
- A member added after the membership snapshot does not get that message through fan-out. They must backfill from history.
- Each message costs up to 199 pending inserts and up to 199 checks. These should be batched. Per-conversation throughput is capped by the conv_seq row lock, which is acceptable at 200 members.
- Pending and messages share the Message Store for transactional simplicity. Moving pending to its own store adds a cross-store consistency problem that this design does not cover.
- The broker retention value is unknown until the worst-case fan-out lag is measured.
- Unknown: whether a push is suppressed when the app is already open. The brief does not say.
- Unknown: the exact endpoint name of the existing history API. This design assumes it exists, as the brief describes.
- Unknown: a client that lost its local state, for example after a reinstall, may not know its own sent seqs. It could then see gaps that are not missed messages.
- Out of scope: typing indicators, read receipts, edits and deletes.