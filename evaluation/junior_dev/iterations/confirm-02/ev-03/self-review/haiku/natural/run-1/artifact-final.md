# Chat message fan-out: online delivery and offline storage

## What this design does

When a user sends a chat message, the server does four things in order:

1. It saves the message once in the Message Store, the existing database that holds conversation history. The save gives the message a sequence number within its conversation.
2. It confirms the save to the sender.
3. In the background, it writes one small "inbox" row for each recipient. The row points to the message. It does not copy the message text.
4. It delivers the message to each recipient. Connected recipients get it live over their WebSocket. Recipients who are not connected get it later, when they reconnect and read their inbox. Offline recipients also get a mobile push notification.

The sender never waits for steps 3 and 4. Because the inbox stores only a pointer, a 200-member conversation stores one copy of the text and up to 199 small rows.

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

   +-----------------------------+                 +------------------------------+
   | PRESENCE STORE (Redis)      |  <-- read (8)   | RECIPIENT'S GATEWAY NODE     |
   | user -> {node, connection}  |                 | (9) sends the message down   |
   | TTL 30 s, refreshed by      |                 |     the recipient's socket   |
   | each 10 s heartbeat         |                 +--------------+---------------+
   | key gone = offline          |                                |
   +-----------------------------+                                v
                                                    +------------------------------+
                                                    | RECIPIENT client             |
                                                    | (12) ack{message_id, conv,   |
                                                    |      seq} --> gateway        |
                                                    |      deletes inbox row       |
                                                    +------------------------------+

   PUSH WORKER -> APNs / FCM. Best effort, no retry, writes nothing to the store.

   RECONNECT
    (13) Client opens a WebSocket to any node and authenticates.
         That node writes PRESENCE before it reads anything.
    (14) SYNC SERVICE reads the user's inbox rows ordered by (conv_id, seq),
         loads bodies from messages in batches, and streams them in seq order
         per conversation, then sends sync-complete. Live deliveries to that
         socket are held until sync-complete.
    (15) Client drops duplicates by message_id, then sends delivered{conv, through_seq}.
         Server deletes that conversation's inbox rows with seq <= through_seq.
    (16) TTL job deletes inbox rows older than 30 days.
```

The diagram has three phases:

- **Send (steps 1 to 4):** the message is saved and the sender is acknowledged. This phase ends at the ack.
- **Fan-out (steps 5 to 12):** the message is queued, a row is written for each recipient, and connected recipients get it live. Recipients who do not acknowledge in time, or who are offline, get a push.
- **Reconnect (steps 13 to 16):** a returning client loads what it missed, confirms it, and the server deletes those inbox rows.

## Key terms

- **Gateway node:** a server that holds WebSocket connections from clients.
- **WebSocket:** a long-lived two-way connection between a client and a server.
- **Heartbeat:** a small message each client sends every 10 seconds to show it is still connected.
- **Message Store:** the existing database that holds conversation history. It is the source of truth.
- **Transaction:** a group of database writes that either all commit or all roll back together.
- **Primary key (PK):** the column that must be unique in a table. A second insert with the same key is rejected.
- **Sequence number (seq):** a counter kept per conversation. Messages in a conversation are ordered by it.
- **Row lock:** when one transaction locks a row, other transactions that need that row wait until it finishes.
- **Outbox:** a table of saved messages that still need to be published to the fan-out queue. Each outbox row is written in the same transaction as its message, so a saved message cannot be lost before it is queued.
- **Relay:** a background process that reads unpublished outbox rows, publishes them to the queue, and marks each row published.
- **Inbox:** a table with one row per (user, conversation, seq). Each row means "this user has not yet received this message." It holds no message text.
- **Fan-out queue:** a durable message queue. Its partition key is `conv_id`, so jobs for one conversation are handled in order.
- **Fan-out job:** one queue message that asks the worker to fan out one saved message.
- **Presence:** a record of which gateway node a user is connected to. It expires when heartbeats stop.
- **TTL (time to live):** a time limit on a record. A record with a 30 s TTL disappears 30 s after it was last refreshed.
- **Ack (acknowledgement):** a reply that confirms something happened. This design uses four kinds, and the name always says which one:
  - *Sender ack:* the server tells the sender its message is saved.
  - *Client ack:* a recipient's client tells the gateway it received a live message.
  - *Queue ack:* the worker tells the queue a fan-out job is finished, so the queue can remove it.
  - *Delivered message:* the client tells the server it has received everything up to a sequence number.
- **Sync:** the reconnect step in which the server sends a client everything in its inbox.
- **Fan-out:** copying a message's pointer into each recipient's inbox and trying to deliver it to them.
- **Push:** a notification sent to a phone through Apple (APNs) or Google (FCM).
- **Idempotent:** an operation that gives the same result whether it runs once or several times. Running it twice does not create a second copy.
- **At-least-once:** each message is delivered one or more times. Clients drop duplicates by `message_id`.

## Where state lives

- **Messages, sequence numbers, dedupe, outbox:** the Message Store. `message_id` is the primary key, so a retry cannot insert a second row. `next_seq` is updated in the same transaction as the insert, so a rolled-back send leaves no gap in the sequence.
- **Undelivered messages per user:** the `inbox` table in the Message Store. It has one row per (user, conversation, seq), holds no message text, and is deleted when the client acknowledges the message. Rows expire after 30 days.
- **Presence:** a Redis key per user holding `{node, connection}`. It has a 30 s TTL that each 10 s heartbeat refreshes. It is temporary and rebuilt from heartbeats, so losing it loses no messages.
- **Socket map:** in memory on each gateway node. It is lost if the node crashes.
- **Fan-out queue:** a durable broker partitioned by `conv_id`, so each conversation is fanned out in sequence order. A job is acknowledged to the queue only after its inbox rows are written and its online deliveries are sent. The queue ack does not wait for the 5 s check.
- **5 s timers:** one per online delivery, held in the fan-out worker's memory. They start after the queue job is acknowledged. If the worker restarts and loses a timer, the only effect is a missed push, because the inbox row still covers delivery.
- **Push:** no stored state.

## Ordering invariants

- **Inbox before presence (steps 7 and 8).** The worker writes the inbox rows first, then reads presence. If it reads "offline," the row already exists, so the user's sync will find it. If it reads "online," the message is sent live. A user who connects just after the read is still covered, because their presence is written, and then their sync runs, after the inbox write.
- **Presence before sync (steps 13 and 14).** The gateway writes presence before it runs the sync query. So any message the worker marked offline has its row in place before that query runs.
- **Live messages wait for sync.** Live deliveries to a reconnecting socket are held until sync-complete. The client receives history in order before anything newer.
- **Sender ack after commit (steps 3 and 4).** The sender is acknowledged once the database transaction commits. It never waits for fan-out or for any recipient.
- **The inbox is the only record of "not yet delivered."** The client's ack deletes the row, and the 5 s check reads the same row.
- **delivered{through_seq} is sent only after sync-complete.** By then the client has received every row up to that sequence number, so the server can delete them safely.

## Failure handling

- **Message Store write fails:** the sender gets an error. Nothing is written to the outbox or inbox, so no one receives the message. The client retries with the same `message_id`.
- **Commit succeeds but the sender ack is lost:** the retry hits the primary key. The existing `message_id` and `seq` are returned. No second row is created and no fan-out runs.
- **Retry uses an id that belongs to another sender or conversation:** rejected as a client error. It is never treated as a duplicate.
- **Crash after commit, before relay:** the outbox row is still unpublished. The relay publishes it after restart. A duplicate publish is harmless, because fan-out is idempotent.
- **Fan-out worker crashes mid-message:** the queue redelivers the job. Inbox writes are idempotent, and some online deliveries repeat. Clients drop the duplicates.
- **Inbox write fails:** the job is not acked and is retried with backoff. The inbox write comes first, so no recipient gets a live delivery without a stored row. Jobs that run out of retries raise an alert.
- **Gateway node crashes:** its sockets close and its presence keys expire within 30 s. Deliveries it was carrying get no client ack, so their inbox rows remain, and the 5 s check sends a push. Affected users reconnect to another node and sync.
- **Presence store is down:** fan-out treats every recipient as offline. Every recipient gets an inbox row and a push. This is noisier, but connected clients see the message on their next sync, so the result stays correct.
- **Client ack is lost:** the row remains until the next sync, which sends a duplicate. The client drops it.
- **Recipient disconnects within the 5 s window:** no client ack arrives, so the push is sent, and the row remains for sync.
- **Live delivery held during sync passes its 5 s deadline:** a delivery to a reconnecting socket waits for sync-complete. If that wait is longer than 5 s, the worker treats it as unacked and sends a push. The push is redundant but harmless.
- **Push fails or times out:** the failure is logged and dropped. Push is never retried and never changes the inbox or the messages.
- **Message Store is down:** sends fail at the sender, and queued fan-out work waits. Nothing is lost.
- **Recipient offline for more than 30 days:** their inbox rows are purged. The message stays in `messages`, and the client recovers it through the existing history reload.
- **Large backlog on reconnect:** sync is paged. Because client acks delete rows as they arrive, an interrupted sync can resume without resending confirmed messages.
- **Hot conversation:** the `conv_seq` row lock serializes sends in one conversation. This is acceptable at 200 members, but lock contention should be monitored.

## Open points

- **Membership at fan-out time:** the recipient list is read from membership when fan-out runs. Members who join after a message is sent receive it through history, not the inbox. Members removed before fan-out are skipped. This needs to be confirmed against the membership rules.
- **Push volume:** one push is sent per message per offline user. Grouping pushes per conversation would reduce noise in busy rooms. This is optional, because push is best effort.