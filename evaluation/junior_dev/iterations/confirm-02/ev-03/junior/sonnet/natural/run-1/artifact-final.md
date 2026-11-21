# Chat message fan-out: online delivery and offline storage

Today clients see new messages only when they reload conversation history. This design adds real-time delivery. A sender's message is written to the Message Store together with an outbox row, and the sender is acked. A relay then moves the outbox row to a queue, and a worker delivers it to each recipient over a WebSocket. If a recipient is offline, or does not ack within 5 seconds, the worker stores a reference in that user's inbox and sends a best-effort push. The inbox is drained, in order, when the client reconnects. The outbox row is what guarantees that an acked message is never lost, even if a process crashes right after the write.

## Fixed requirements

- Each client holds a WebSocket to one of several gateway nodes and sends a heartbeat every 10 seconds. A user is offline after 30 seconds with no heartbeat. One device per user in this version.
- A conversation has at most 200 members. The sender is not a recipient of their own message.
- The sender is acked only after the Message Store write commits. The ack carries the message id and the seq. If the write fails, the sender gets an error and no one receives anything. The client retries with the same client-generated message id, and a retry never creates a second copy.
- Fan-out is not on the sender's request path, and the sender's ack never waits for a recipient.
- An online recipient's client acks each message. No ack within 5 seconds means the recipient is treated as offline for that message.
- For offline recipients, missed messages are kept for up to 30 days and a mobile push is sent. Push is best effort, never retried, and a failed push never affects what is stored.
- On reconnect the client receives everything it missed, in seq order within each conversation.
- Delivery is at-least-once. Clients drop duplicates by message id.
- Out of scope: typing indicators, read receipts, edits and deletes.

## Terms

- **Message Store**: the existing conversation history database. Source of truth for messages.
- **seq**: a per-conversation sequence number given to each message when it is stored. It defines message order.
- **Outbox**: a table in the Message Store. One row per stored message that still needs fan-out. The row has a `sent_at` field, empty until the message is published to the queue.
- **Outbox Relay**: a single process that moves outbox rows to the Fan-out Queue.
- **Fan-out Queue**: an at-least-once queue, partitioned by conversation id, so one conversation is handled in seq order.
- **Fan-out Worker**: consumes one queue message at a time and delivers it to every recipient.
- **Gateway node**: a server holding client WebSockets. It also accepts internal requests from workers: deliver, close session, drain.
- **Presence Store**: maps user to gateway node. An entry expires 30 seconds after its last heartbeat.
- **Offline Inbox**: per recipient, holds references (conv, seq, msgId), not bodies. Entries expire after 30 days.
- **Drain**: the gateway reads a user's inbox, loads each body from the Message Store, streams the entries in order and deletes each one once the client acks it.
- **Push Service**: APNs or FCM, which sends mobile push notifications.

## Diagram

```
 SENDER                                                    RECIPIENT (online or offline)
+----------+                                              +-----------+
| Client S |                                              | Client R  |
+----------+                                              +-----------+
  |  ^                                                      ^  |   ^  |
  |  | 3 ack(msgId, seq)                        7 deliver   |  |   |  | R1 connect
  |  |   or error                               8 ack <5s   |  |   |  | R2 hello
  |  |                                                      |  v   |  v    heartbeat/10s
  |  |                                                   +---------------+
  |  |                                                   | Gateway node  |  (n nodes, WebSocket,
  |  |                                                   |  G1 .. Gn     |   one session per user)
  |  |                                                   +---------------+
  |  |                                                     ^  |  |  ^  |
  | 1 send(clientMsgId, conv, body)             7 deliver   |  |  |  |  R3/R4 drain, R5 ack
  v  |                                                      |  |  |  |
+----------------+   2 one transaction:    +--------------+ |  |  |  |
| Send API       |---------------------->  | Message Store| |  |  |  |
| (request path  |   - insert message       | (existing    | |  |  |  |
|  ends at the   |     UNIQUE(conv,         |  history DB) | |  |  |  |
|  ack)          |     clientMsgId)         |  messages    | |  |  |  |
+----------------+   - assign seq           |  + OUTBOX    | |  |  |  |
                     - insert outbox row    +--------------+ |  |  |  |
                              |                              |  |  |  |
              ================|== sender's path ends here ====|==|==|==|=========
                              | 4 relay polls outbox         |  |  |  |
                              v                              |  |  |  |
                      +----------------+                     |  |  |  |
                      | Outbox Relay   |                     |  |  |  |
                      +----------------+                     |  |  |  |
                              | 4 publish (key = conv id)    |  |  |  |
                              v                              |  |  |  |
                      +----------------+                     |  |  |  |
                      | Fan-out Queue  |  at-least-once,     |  |  |  |
                      | partition/conv |  ordered per conv   |  |  |  |
                      +----------------+                     |  |  |  |
                              | 5 consume                    |  |  |  |
                              v                              |  |  |  |
                      +----------------+  6 who is online,   |  |  |  |
                      | Fan-out Worker |<--- on which node?  |  |  |  |
                      |                |    +-----------+    |  |  |  |
                      | members(conv)  |    | Presence  |    |  |  |  |
                      |  minus sender  |--->| Store     |<---+--+--+--+- R6 registers presence;
                      +----------------+    | user->node|       |  |     heartbeats refresh, TTL 30 s
                       |   |    |           +-----------+       |  |
        7 deliver -----+   |    | 9 no ack in 5 s, or offline   |  |
        via node           |    v                               |  |
                           |  +-----------------+  R3 read       |  |
                           |  | Offline Inbox   |----------------+--+
                           |  | per user: (conv,|  sorted by (conv, seq)
                           |  | seq, msgId), TTL|  R5 delete after ack
                           |  | 30 days         |
                           |  +-----------------+
                           | 10 best-effort push, no retry, result ignored
                           v
                    +-----------------+
                    | Push Service    |---> mobile push to Client R
                    | (APNs / FCM)    |
                    +-----------------+
```

## How it runs

### Send (steps 1 to 3)

1. **The client sends** (clientMsgId, conversation, body). The client generated the id, so a retry can reuse it.
2. **The Send API writes in one Message Store transaction**: the message, the outbox row, and the seq. The seq comes from a counter row per conversation, incremented under a row lock, so concurrent sends get distinct, gap-free seqs, and a rollback undoes the increment. The message is unique on (conversation, clientMsgId). A duplicate returns the existing msgId and seq and creates no new row or outbox entry. This assumes the store supports a local transaction. If it does not, use its change feed as the outbox.
3. **After commit, the sender gets ack(msgId, seq).** If the write fails or times out, the sender gets an error and nothing is stored or fanned out, and the client retries with the same clientMsgId. If the Send API crashes after commit but before the ack, the retry hits the unique key and gets the original ack.

### Fan-out (steps 4 to 10)

4. **The relay publishes outbox rows.** One relay polls for rows with `sent_at` empty, oldest first, publishes each to the queue keyed by conversation id, then sets `sent_at`. If it crashes it is restarted, and unsent rows wait in the outbox, so a crash after commit never loses a message. A crash between publish and setting `sent_at` causes a duplicate publish, which clients drop. Only one relay runs in this version, so two relays never publish one conversation out of order.
5. **The worker takes one queue message**, loads members(conversation) at that moment, and drops the sender. Anyone who joined or left since the send is treated by the membership now. The worker keeps the queue message uncommitted until every recipient is either acked or in the inbox. If the worker crashes, the queue redelivers the message. Recipients who already got it may get it again, and the client drops the duplicate.
6. **For each recipient, the worker looks up presence.** Recipients are handled in parallel. If the lookup fails or times out, the recipient is treated as offline. This is safe because the inbox is drained on reconnect.
7. **Online: the worker sends a deliver request** to that user's gateway node.
8. **The gateway pushes the message to the client.** The client's ack goes to the gateway, which answers the worker's request. The worker waits up to 5 seconds. A late ack is ignored, because the inbox entry already exists and the client drops the later duplicate.
9. **Offline, or no ack in 5 seconds: the worker writes an inbox entry** (idempotent on user, conversation and seq). If the write fails, the worker does not commit the queue message, the queue redelivers it and the whole message is processed again. No push is sent for that recipient until the entry is written. After a 5-second timeout the worker also asks that user's gateway node to close the session and clear presence. This stops later messages going out live ahead of the missed one. The client reconnects and drains in order. A recipient who got a later message before the timeout may briefly see a gap, which the drain fills. The client orders by seq.
10. **After the inbox write, the worker sends a push.** Push is best effort. A failure is logged and ignored, nothing is retried, and nothing stored is touched. After the inbox write the worker also re-checks presence, and if the user is now online it sends that node a drain request. This closes the gap where an entry lands just after a drain's last read. The push goes out either way, and a push to a user who has just reconnected is harmless.

### Reconnect (steps R1 to R6)

- **R1** The client opens a WebSocket to any gateway node. The user is not in presence yet.
- **R2** The client says hello. It may include its last seq per conversation. That is used only for the history fallback described below, and never to skip inbox entries, because the inbox is complete and the client drops duplicates.
- **R3, R4** The gateway reads the user's inbox ordered by (conversation, seq), loads each body from the Message Store and streams the entries.
- **R5** The client acks each entry and the gateway deletes it. If the drain is interrupted, unacked entries remain and are sent again next time.
- **R6** The gateway re-reads the inbox until a read returns empty. Only then does it register presence and start live delivery. Until then workers see the user as offline and write inbox entries, which the re-reads pick up, so live messages never overtake the drain.
- **After 30 days**, inbox entries have expired. The client falls back to reloading history from the Message Store, which keeps the messages.

### Where each piece of state lives

| State | Lives in | Notes |
|---|---|---|
| Message body, seq, client msgId | Message Store | Source of truth. Unique on (conversation, clientMsgId), which makes retries idempotent. |
| "Needs fan-out" marker | Outbox table in the Message Store | Written in the message's transaction, so an acked message is never lost. |
| Queue position | Fan-out Queue | Keyed by conversation id, so one conversation is processed in seq order. |
| Online/offline, user to gateway node | Presence Store | Registered when the reconnect drain finishes. Refreshed by each heartbeat, expires after 30 s. |
| Missed messages | Offline Inbox | References only. Expire after 30 days. |
| Push | Nowhere | Fire and forget. |
| Duplicate suppression | Client | Remembers the msgIds it has seen. |

### Failures that cross steps

- **Gateway node dies.** Sessions drop and presence entries expire within 30 seconds. Deliveries sent to the dead node get no ack within 5 seconds and go to the inbox. Clients reconnect to another node and drain.
- **Stale presence** (user gone, TTL not yet expired). The 5-second ack timeout sends the message to the inbox.
- **Presence says offline, but the user just reconnected.** Re-reads during the drain and the worker's re-check after the inbox write (step 10) cover this.
- **Sender.** Excluded from the recipient list, so the sender gets no fan-out or inbox entry for their own message.

### Delivery guarantees

- Delivery is at-least-once. Duplicates can come from the relay, queue redelivery, worker retry, a late ack or a lost client ack. The client drops them by msgId.
- Order within a conversation comes from seq. Queue partitioning keeps the live stream in order, and the inbox drain is sorted by (conversation, seq).
- A message has at most 199 recipients (the 200-member limit minus the sender). Recipients are handled in parallel, so one slow recipient does not delay the others in the same message.
- A slow recipient does hold its queue partition for up to 5 seconds, so later messages in that conversation, and others on that partition, wait. This is accepted to keep ordering simple.

## Open questions

- Where the 200-member limit is enforced (for example, when members are added) is outside this design. We assume it holds.
- How long the client remembers msgIds is not decided. If it forgets one and gets a redelivery, the user may see a duplicate.
