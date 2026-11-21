# Chat message fan-out: online delivery and offline storage

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
                              | 4 relay polls/tails outbox   |  |  |  |
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
                      |  minus sender  |--->| Store     |<---+--+--+--+- heartbeats refresh
                      +----------------+    | user->node|       |  |     entry, TTL 30 s
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

Numbered flow
  SEND       1 client sends with a client-generated msgId
             2 Send API writes message + outbox row in ONE Message Store transaction
               (duplicate (conv, clientMsgId) returns the existing msgId and seq,
                and creates no new row or outbox entry)
             3 after commit, ack(msgId, seq) goes to the sender; on failure, an error
  FAN-OUT    4 relay moves outbox rows to the queue, then marks them sent
             5 worker takes one message, loads members(conv), drops the sender
             6 for each recipient, looks up presence
             7 online: send over that user's gateway node
             8 recipient client acks; the worker waits up to 5 s
             9 offline, or no ack in 5 s: write an inbox entry (idempotent on user+conv+seq)
            10 after the inbox write: send a push (best effort)
  RECONNECT  R1 client opens a WebSocket; gateway registers presence
             R2 client says hello (optionally with last seq per conversation)
             R3 gateway reads the user's inbox, ordered by (conv, seq)
             R4 gateway streams the entries to the client
             R5 client acks each; gateway deletes the acked entries
             R6 gateway re-reads the inbox until it is empty, then continues live delivery
```

## Notes

### Where each piece of state lives

| State | Lives in | Notes |
|---|---|---|
| Message body, per-conversation seq, client msgId | Message Store | Source of truth. Unique on (conversation, clientMsgId), which makes retries idempotent. |
| "Needs fan-out" marker | Outbox table in the Message Store | Written in the same transaction as the message, so an acked message is never lost. This assumes the store can do a local transaction. If it can't, use its change feed as the outbox. |
| Queue position | Fan-out Queue | Keyed by conversation id, so one conversation's messages are processed in seq order. |
| Online/offline, user to gateway node | Presence Store | Entry is refreshed by each 10 s heartbeat and expires after 30 s. |
| Missed messages | Offline Inbox | Per recipient. Holds references (conv, seq, msgId), not body copies. The body is read from the Message Store when drained. Entries expire after 30 days. |
| Push | Nowhere | Fire and forget. |
| Duplicate suppression | Client | Remembers the msgIds it has seen. |

### Failures

- **Message Store write fails or times out.**
  - The sender gets an error.
  - No outbox row exists, so nothing is fanned out.
  - The client retries with the same clientMsgId.
  - If the first attempt actually committed but the ack was lost, the retry hits the unique key and gets back the same msgId and seq. No second copy is created and no second fan-out starts.
- **Send API crashes after commit but before the ack.** The message is stored and will be fanned out. The client retries and receives the original ack.
- **Crash after commit, before fan-out.** The outbox row is still unsent, so the relay publishes it later. A crash between publish and "mark sent" means a duplicate publish, which clients drop by msgId.
- **Worker crashes mid-message.** The queue redelivers the message. Inbox writes are idempotent. Recipients who already got the message may get it again, and the client drops the duplicate.
- **Membership.** Members are read at fan-out time. Anyone who joined or left between the send and the fan-out is treated by the membership at that moment.
- **No ack in 5 s from an online recipient.**
  - The worker writes the inbox entry and then sends a push.
  - The gateway closes that user's session and clears presence. This stops later messages from going out live ahead of the missed one. The client reconnects and drains in order.
  - A recipient who received a later message before the timeout may have seen a gap briefly. The reconnect drain fills it, and the client orders by seq.
- **Gateway node dies.**
  - Sessions drop.
  - Presence entries expire within 30 s.
  - Deliveries sent to the dead node get no ack within 5 s and go to the inbox.
  - Clients reconnect to another node and drain.
- **Presence says offline, but the user just reconnected.**
  - After writing an inbox entry, the worker re-checks presence. If the user is now online, it tells that node to drain.
  - The gateway also re-reads the inbox until it is empty after reconnect (step R6).
  - Together these close the window where an entry lands just after the drain read.
- **Push fails.** The failure is logged and ignored. Nothing is retried and nothing stored is touched. The inbox entry is written before the push is attempted.
- **Reconnect drain interrupted.** Entries are deleted only after the client acks them, so unacked entries remain and are sent again next time.
- **Reconnect after 30 days.** Inbox entries have expired. The client falls back to reloading history from the Message Store, which keeps the messages.
- **Sender.** The sender is excluded when building the recipient list, so they get no fan-out or inbox entry for their own message.

### Delivery guarantees

- Delivery is at-least-once. Duplicates can come from the relay, queue redelivery, worker retry, or a lost client ack. The client drops them by msgId.
- Ordering within a conversation comes from the per-conversation seq. Queue partitioning keeps the live stream in order, and the inbox drain is sorted by (conv, seq).
- Fan-out cost per message is at most 199 recipients. Each recipient is handled independently, so one slow recipient waiting on its 5 s ack does not delay the others.
