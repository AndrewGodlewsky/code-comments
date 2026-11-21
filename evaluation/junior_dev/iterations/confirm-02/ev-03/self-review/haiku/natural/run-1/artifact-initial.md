# Chat message fan-out: online delivery and offline storage

## Flow diagram

```
 +-----------+   (1) send{message_id, conv, body}    +----------------------------+
 | SENDER    |-------------------------------------->| GATEWAY NODE (sender's)    |
 | client    |<------(4) ack{message_id, seq}--------| WebSocket, heartbeat       |
 +-----------+                                       +-------------+--------------+
                                                                   | (2)
                                                                   v
                                                     +----------------------------+
                                                     | MESSAGE SERVICE (send)     |
                                                     | idempotent insert, seq     |
                                                     +-------------+--------------+
                                                                   | (3) one DB transaction
                                                                   v
 +---------------------------------------------------------------------------------+
 | MESSAGE STORE (existing DB, durable)                                            |
 |   messages(message_id PK, conv_id, seq, sender_id, body)                        |
 |   conv_seq(conv_id PK, next_seq)                  row lock per conversation     |
 |   outbox(message_id PK, conv_id, seq, published_at NULL)                        |
 |   inbox(user_id, conv_id, seq) PK, message_id, created_at    (no body copy)     |
 +------------------------------------+--------------------------------------------+
                                      | (5) outbox relay publishes, marks published
                                      v
                          +-------------------------+
                          | FAN-OUT QUEUE           |  partition = conv_id
                          +------------+------------+
                                       | (6) consume, ack only when done
                                       v
 +---------------------------------------------------------------------------------+
 | FAN-OUT WORKER  (members minus sender, at most 199)                             |
 |  (7)  batch upsert inbox row for every recipient  (durable before any delivery) |
 |  (8)  read PRESENCE for each recipient                                          |
 |  (9)  online: deliver{message} to the recipient's gateway node                  |
 |  (10) 5 s deadline: inbox row gone = acked; row still there = treat offline     |
 |  (11) offline, or deadline passed unacked: push request --> PUSH WORKER         |
 +---------------------------------------------------------------------------------+
        ^                                   |
        | read in (8)                       | (9) over the node's channel
 +------+-----------------------------+     v
 | PRESENCE STORE (Redis)             |  GATEWAY NODE (recipient's)
 | user -> {node, connection}         |  WebSocket write to recipient client
 | TTL 30 s, refreshed every 10 s     |     |
 | key expiry = offline               |     v
 +------------------------------------+  RECIPIENT client
                                         (12) ack{message_id, conv, seq}
                                              gateway deletes inbox row (user, conv, seq)

 PUSH WORKER -> APNs / FCM. Best effort, no retry, writes nothing to the store.

 RECONNECT
  (13) Client opens WebSocket to any node and authenticates.
       The gateway writes PRESENCE before it reads anything.
  (14) SYNC SERVICE reads inbox rows for the user, ordered by (conv_id, seq),
       loads bodies from messages in batches, and streams them in seq order per
       conversation, then sends sync-complete. Live deliveries to that socket are
       held until sync-complete.
  (15) Client drops duplicates by message_id and sends delivered{conv, through_seq}.
       Server deletes inbox rows with seq <= through_seq for that conversation.
  (16) TTL job deletes inbox rows older than 30 days.
```

## Where state lives

- **Messages, sequence numbers, dedupe, outbox:** the existing Message Store, which is the source of truth. `message_id` is the primary key, so a retry cannot insert a second row. `next_seq` is updated in the same transaction as the insert, so a rolled-back send leaves no gap.
- **What each user has not yet confirmed:** the `inbox` table in the Message Store, one row per (user, conversation, seq). It holds no body copy and is deleted on ack. It is the durable record of "still to deliver". It expires after 30 days.
- **Presence:** a Redis key per user holding `{node, connection}`, with a 30 s TTL refreshed by each 10 s heartbeat. It is ephemeral and rebuilt from heartbeats.
- **Socket map:** in memory on each gateway node.
- **Fan-out queue:** a durable broker partitioned by `conv_id`, so each conversation is fanned out in seq order. A job is acked only after all inbox rows are written and online attempts are dispatched.
- **5 s deadlines:** in the fan-out worker's memory. A lost deadline only loses a push, and the inbox row still covers delivery.
- **Push:** no state.

## Ordering invariants

- The inbox row is written (step 7) before presence is read (step 8). The gateway sets presence before the sync query (step 14). Together these ensure that a message is either delivered live or found by sync, never missed between the two.
- The sender's ack (step 4) follows the commit (step 3). It never waits for fan-out or recipients.
- The inbox is the single source for "not yet delivered". The ack deletes the row, and the 5 s check reads the same row.

## Failure handling

- **Message Store write fails:** the sender gets an error. Nothing is written to outbox or inbox, so no one receives anything. The client retries with the same `message_id`.
- **Commit succeeds but the ack is lost:** the retry hits the primary key, the existing `message_id` and `seq` are returned, and no second row or fan-out occurs.
- **Retry carries an id owned by another sender or conversation:** rejected as a client error. It is never treated as a duplicate.
- **Crash after commit, before relay:** the outbox row is still unpublished, and the relay publishes it on restart. Duplicate publishes are harmless because fan-out is idempotent.
- **Fan-out worker crashes mid-message:** the queue redelivers the job. Inbox upserts are idempotent, and some online deliveries repeat. Clients drop duplicates.
- **Inbox write fails:** the job is not acked and is retried with backoff. Because the write comes first, no recipient receives an online delivery without a stored row. Alert on jobs that exhaust retries.
- **Gateway node crashes:** its sockets vanish and its presence keys expire within 30 s. In-flight deliveries never get an ack, so their rows remain. Affected users reconnect to another node and sync.
- **Presence store is down:** fan-out treats every recipient as offline. Inbox rows and push go out for everyone. This is noisier but still correct.
- **Client ack lost:** the row remains until the next sync, which causes a duplicate. Clients drop it.
- **Recipient disconnects inside the 5 s window:** no ack, so the push fires and the row remains for sync.
- **Push fails or times out:** logged and dropped. It never retries and never touches the inbox or messages.
- **Message Store is down:** sends fail at the sender. Queued fan-out work waits. Nothing is lost.
- **Recipient offline longer than 30 days:** the inbox rows are purged. The message stays in `messages`, and the client recovers through the existing history reload.
- **Large backlog on reconnect:** sync is paged. Ack-driven deletion lets an interrupted sync resume without resending confirmed items.
- **Hot conversation:** the `conv_seq` row lock serializes sends per conversation. This is acceptable at 200 members, but contention should be watched.

## Open points

- The recipient set is read from membership at fan-out time. Members who join after a send get the message through history, not inbox. Removed members are skipped at fan-out. Confirm that this matches the membership rules.
- Push is sent per message per offline user. Coalescing pushes per conversation would reduce noise in busy rooms. This is optional, because push is best effort.
