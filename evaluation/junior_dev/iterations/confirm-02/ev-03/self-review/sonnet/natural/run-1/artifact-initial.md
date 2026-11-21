```text
                                SENDER PATH (synchronous)
 +----------+  1 send(msg_id, conv, body)   +-----------+
 | Sender   |------------------------------>| Gateway   |
 | client   |<------------------------------| node A    |
 +----------+  4 ack(msg_id, seq)           +-----+-----+
                  or error                        | 2 write(client msg_id)
                                                  v
                                   +-----------------------------+
                                   | Message Store (existing DB) |
                                   |  messages: seq per conv,    |
                                   |    UNIQUE(conv, msg_id)     |
                                   |  outbox: 1 row per message  |
                                   |  3 one transaction = both   |
                                   +--------------+--------------+
                                                  |
 - - - - - - - - - - - - - - - - - - - - - - - - | - - - - - - - - - - - - - - -
                  FAN-OUT PATH (async, off the request path)
                                                  | 5 outbox relay polls
                                                  v    unpublished rows
                                   +-----------------------------+
                                   | Fan-out Queue               |
                                   | partitioned by conv_id,     |
                                   | at-least-once               |
                                   +--------------+--------------+
                                                  | 6 consume
                                                  v
                                   +-----------------------------+   7 members(conv)
                                   | Fan-out Worker              |-----> Membership
                                   | per recipient (not sender): |   8 lookup(user)
                                   |                             |-----> Presence Registry
                                   +---+-----------------+-------+       (user -> gateway,
                                       |                 |               TTL 30s, refreshed
                       online          |                 | offline       by heartbeat)
                  9a deliver(msg)      |                 | 9b append pointer
                                       v                 v
                              +-----------------+   +------------------------+
                              | Gateway node B  |   | Offline Inbox          |
                              | (recipient's)   |   | key: user, conv, seq   |
                              +--------+--------+   | value: msg_id          |
                          10a WS push  |            | TTL 30 days            |
                                       v            +-----------+------------+
                              +-----------------+               | 10b after the write
                              | Recipient       |               v
                              | client          |      +------------------+
                              +--------+--------+      | Push Service     |
                       11a client ack  |               | (APNs/FCM)       |
                       within 5s -> done               | one try, no retry|
                       no ack in 5s -> go to 9b        +------------------+

 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
                              RECONNECT PATH
 +-----------+ R1 connect + heartbeat  +-----------+ R2 register user -> node in Presence
 | Recipient |------------------------>| Gateway   | R3 read Offline Inbox for user,
 | client    |<------------------------| node C    |    sort by (conv, seq)
 +-----------+ R4 stream messages,     +-----------+ R5 fetch bodies from Message Store
               in seq order per conv                 R6 client acks each -> delete entry
               R7 client drops duplicates by msg_id  R8 re-drain once after any "nudge"
```

## Where state lives

| State | Location | Notes |
|---|---|---|
| Message body, seq, client msg_id | Message Store | Source of truth. `UNIQUE(conversation, client msg_id)` makes retries idempotent. |
| "Needs fan-out" marker | Outbox table in Message Store | Written in the same transaction as the message. Marked published by the relay. |
| In-flight fan-out work | Fan-out Queue | Partitioned by conversation so one conversation is handled in seq order. |
| Who is online, and on which node | Presence Registry | Key `user -> node`, TTL 30s, refreshed on each 10s heartbeat. Deleted on clean socket close. |
| Missed messages | Offline Inbox | Pointers `(user, conv, seq, msg_id)` with a 30-day TTL. Bodies stay in the Message Store. |
| Seen message ids | Client | Drops duplicates. |
| Push attempts | Nowhere | Fire and forget, not recorded. |

## Rules that make it correct

- **Send (steps 1-4).** The gateway writes the message and the outbox row in one transaction. It acks only after the commit, and the ack carries `msg_id` and `seq`. The ack never waits on fan-out.
- **Retry.** A retry with the same `msg_id` hits the unique key. The store returns the existing `seq` and creates no second message or outbox row. This also covers a gateway crash after commit but before the ack.
- **Recipients.** The worker takes the membership list (200 at most) and skips the sender.
- **Online delivery (9a-11a).** The worker asks the recipient's gateway to deliver. The gateway pushes over the WebSocket and waits for the client ack. An ack ends that recipient's work. The worker does not block on one recipient's 5s wait. Recipients are handled concurrently.
- **Offline path (9b-10b).** The worker takes this path in three cases:
  - Presence has no entry.
  - The gateway call fails.
  - No client ack arrives within 5s.
  
  The worker writes the inbox entry first. Only after that write succeeds does it request a push. A push failure is logged and ignored. It never touches the inbox and is never retried.
- **Ordering.** A recipient with pending inbox entries for a conversation gets later messages in that conversation appended to the inbox too, with no live attempt. This stops a live message jumping ahead of an earlier missed one. The inbox key `(user, conv, seq)` sorts by seq, so reconnect delivery is in order within each conversation.
- **Duplicates.** Delivery is at-least-once. A live delivery can be retried after a timeout, or a queue message can be redelivered. The client drops repeats by `msg_id`.

## Failure handling

| Failure | Result |
|---|---|
| Message Store write fails | Gateway returns an error. There is no message and no outbox row, so nobody receives anything. The client retries with the same `msg_id`. |
| Gateway dies after commit, before ack | The client times out and retries. The unique key returns the original `seq`. Fan-out is unaffected because the outbox row exists. |
| Process dies after commit | The outbox row is still unpublished, so the relay publishes it on its next poll. The ack guarantee holds. |
| Relay dies or publishes twice | Another relay instance resumes from unpublished rows. A double publish is a duplicate delivery, which clients drop. |
| Worker dies mid-fan-out | The queue message is not acknowledged, so it is redelivered and processed again. Recipients already served may get a duplicate. |
| Recipient gateway dies | The deliver call fails or times out, so the recipient takes the offline path. Presence expires within 30s. |
| Client ack lost | The worker treats the recipient as offline after 5s. The message goes to the inbox and the client may see it twice. |
| Presence stale (user gone, entry not yet expired) | The live attempt gets no ack within 5s, so the message goes to the inbox. |
| Inbox write fails | The worker does not acknowledge the queue message. Redelivery retries the whole message. Push is not requested. |
| Push fails | Nothing happens. The inbox entry is already durable. |
| Reconnect races with fan-out | The worker saw "offline", the client then reconnects and drains an empty inbox, and the worker then writes the entry. To close this, the worker re-checks presence after every inbox write. If the user is now online, it sends a "nudge" to their gateway. The gateway re-drains the inbox (R8). |
| Reconnect drain interrupted | Entries are deleted only after the client acks them. The next connect resumes from what is left. |
| Inbox entry older than 30 days | The entry expires. The message remains in conversation history, and the client fills the gap by reloading history. |

## Assumptions

- The Message Store assigns `seq` inside the write transaction. The outbox needs a database that can commit two tables atomically. If the store cannot, use its change-data-capture feed as the outbox instead.
- One device per user. Multiple devices would need an inbox per device.
- Live delivery order between different messages can still vary when a message is retried. Clients should render by `seq` and use the inbox drain to fill gaps.
