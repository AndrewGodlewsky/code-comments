## Chat message fan-out: online delivery and offline storage

**In one paragraph.** When a sender presses send, a gateway node saves the message and a "needs fan-out" marker (an outbox row) in one database transaction, then acks the sender. A background relay copies each marker into a queue. A worker takes each queue job and delivers the message to every recipient. A recipient who is online gets it over their WebSocket. For a recipient who is offline, the worker stores a pointer to the message in an inbox and sends a best-effort push notification. When that recipient reconnects, the gateway sends them everything in the inbox, in order.

**Terms**

- `msg_id`: an id the client generates for each message. Retries reuse it, which is how duplicates are detected.
- `seq`: a number the Message Store assigns to each message, increasing within one conversation. It defines message order.
- "Acknowledged" (sender side) means the sender received the ack in step 3 below. "Acked" (recipient side) means the recipient's client confirmed it received a message.
- "Offline path": storing an inbox entry and requesting a push, instead of delivering live.

**Components**

- **Gateway node:** one of several servers. Each client keeps a WebSocket to one gateway node and sends a heartbeat every 10 seconds.
- **Message Store:** the existing conversation-history database and the source of truth.
- **Outbox:** a table in the Message Store with one row per message whose fan-out is not yet queued.
- **Relay:** a small process that copies unpublished outbox rows into the queue and marks them published.
- **Fan-out Queue:** a durable, at-least-once queue, partitioned by conversation. A job is removed only when a worker marks it done.
- **Fan-out Worker:** takes a queue job and delivers that message to every recipient.
- **Membership:** the service that lists a conversation's members (at most 200).
- **Presence Registry:** maps each online user to the gateway node holding their socket. An entry expires after 30 seconds unless a heartbeat refreshes it, so a user with no heartbeat for 30 seconds counts as offline.
- **Offline Inbox:** per-user pointers to messages the user has not yet acked. It holds pointers only. Bodies stay in the Message Store.
- **Push Service:** APNs/FCM, used for mobile notifications.

```text
 SEND PATH (synchronous: the sender waits)

 +--------+  1 send(msg_id, conv, body)   +---------+
 | Sender |------------------------------>| Gateway |
 | client |<------------------------------| node A  |
 +--------+  3 ack(msg_id, seq) or error  +----+----+
                                               |
                  2 ONE transaction: write the message + an outbox row
                                               v
                          +------------------------------------+
                          | Message Store (existing DB)        |
                          |  messages: seq per conversation,   |
                          |            UNIQUE(conv, msg_id)    |
                          |  outbox:   one row per message     |
                          +------------------+-----------------+
                                             |
 - - - - - - - - - - - - - - - - - - - - - - | - - - - - - - - - - - - - - -
 FAN-OUT PATH (asynchronous: nobody waits)   | 4 relay polls unpublished
                                             v   outbox rows, queues them
                          +------------------------------------+
                          | Fan-out Queue                      |
                          | partitioned by conv, at-least-once |
                          +------------------+-----------------+
                                             | 5 worker takes a job
                                             v
                          +------------------------------------+
                          | Fan-out Worker                     |
                          |  6 get member list from Membership |
                          |  then for each member except the   |
                          |  sender:                           |
                          |  7 ask Presence Registry: online?  |
                          +----+-----------------------+-------+
                        online |                       | offline
                  8a deliver   |                       | 8b write inbox entry
                               v                       v
                      +----------------+     +-----------------------------+
                      | Gateway node B |     | Offline Inbox               |
                      | (recipient's)  |     | key:   (user, conv, seq)    |
                      +-------+--------+     | value: msg_id               |
                              |              | TTL:   30 days              |
                              | 9a WebSocket +--------------+--------------+
                              v   push                      |
                      +----------------+                    | 9b only after
                      | Recipient      |                    |    8b succeeds
                      | client         |                    v
                      +-------+--------+          +------------------+
                              |                   | Push Service     |
                              | 10a client acks   | one try, no retry|
                              v   (back to B,     +------------------+
                                  then the worker)
                  ack within 5s: done
                  no ack in 5s:  do 8b instead

 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
 RECONNECT PATH (a recipient comes back online)

 +-----------+  R1 connect + heartbeat  +-----------+
 | Recipient |------------------------->| Gateway   |
 | client    |<-------------------------| node C    |
 +-----------+  R4 stream messages      +-----------+
                (seq order per conv)

 R2 gateway registers user -> node C in the Presence Registry (before R3)
 R3 gateway reads the user's Offline Inbox, sorted by (conv, seq)
 R4 gateway fetches each body from the Message Store and streams it
 R5 client acks each message; gateway deletes that inbox entry
 R6 client drops any msg_id it has already seen
 R7 if a worker sends a "nudge" (see Failure handling), the gateway
    drains the inbox again (repeats R3-R6)
```

## Where state lives

| State | Location | Notes |
|---|---|---|
| Message body, `seq`, client `msg_id` | Message Store | Source of truth. `UNIQUE(conversation, msg_id)` makes retries idempotent. |
| "Needs fan-out" marker | Outbox table in Message Store | Written in the same transaction as the message. The relay marks it published. |
| In-flight fan-out work | Fan-out Queue | Partitioned by conversation, so one conversation's messages are handled in `seq` order. |
| Who is online, and on which node | Presence Registry | `user -> node`, TTL 30s, refreshed by each 10s heartbeat. Deleted on clean socket close. |
| Missed messages | Offline Inbox | Pointers `(user, conv, seq, msg_id)` with a 30-day TTL. |
| Seen message ids | Client | Used to drop duplicates. |
| Push attempts | Nowhere | Fire and forget, not recorded. |

## Rules that make it correct

- **Send (steps 1-3).** The gateway writes the message and the outbox row in one transaction. It acks only after the commit, and the ack carries `msg_id` and `seq`. The ack never waits on fan-out. If the write fails, the sender gets an error and no one receives anything.
- **Retry.** A retry with the same `msg_id` hits the unique key. The store returns the existing `seq` and creates no second message or outbox row. This also covers a gateway crash after commit but before the ack.
- **Why the outbox.** If the gateway wrote the message and then separately published to the queue, a crash between the two could lose the publish. Because the marker commits with the message, every acknowledged message has a marker, and the relay will eventually queue it.
- **Recipients (steps 6-7).** The worker reads the member list, skips the sender, and handles the remaining recipients concurrently, so one slow recipient does not block the others.
- **Online delivery (steps 8a-10a).** The worker asks the recipient's gateway to deliver. The gateway pushes the message over the WebSocket and waits up to 5 seconds for the client's ack. An ack ends that recipient's work.
- **Offline path (steps 8b-9b).** The worker takes this path in three cases:
  - Presence has no entry for the user.
  - The call to the recipient's gateway fails.
  - No client ack arrives within 5 seconds.

  The worker writes the inbox entry first. Only after that write succeeds does it request a push. A push failure is logged and ignored. It never touches the inbox and is never retried.
- **Ordering.** If a recipient already has pending inbox entries for a conversation, later messages in that conversation go straight to the inbox with no live attempt. This stops a live message from jumping ahead of an earlier missed one. The inbox key `(user, conv, seq)` sorts by `seq`, so reconnect delivery is in order within each conversation.
- **Duplicates.** Delivery is at-least-once. A live delivery can be repeated after a timeout, or a queue job can be redelivered. The client drops repeats by `msg_id`.

## Failure handling

| Failure | Result |
|---|---|
| Message Store write fails | The gateway returns an error. There is no message and no outbox row, so nobody receives anything. The client retries with the same `msg_id`. |
| Gateway dies after commit, before ack | The client times out and retries. The unique key returns the original `seq`. Fan-out is unaffected because the outbox row exists. |
| Any process dies after commit | The outbox row is still unpublished, so the relay queues it on its next poll. An acknowledged message still reaches everyone. |
| Relay dies or publishes twice | Another relay instance resumes from the unpublished rows. A double publish causes duplicate deliveries, which clients drop. |
| Worker dies mid-fan-out | The queue job is not marked done, so it is redelivered and processed again. Recipients already served may get a duplicate. |
| Recipient's gateway dies | The deliver call fails or times out, so the recipient takes the offline path. Presence expires within 30s. |
| Client ack lost | After 5s the worker treats the recipient as offline. The message goes to the inbox, and the client may see it twice. |
| Presence is stale (user gone, entry not yet expired) | The live attempt gets no ack within 5s, so the message goes to the inbox. |
| Inbox write fails | The worker does not mark the queue job done. Redelivery retries the whole message. No push is requested. |
| Push fails | Nothing happens. The inbox entry is already durable. |
| Reconnect races with fan-out | Sequence: the worker sees the user as offline, the client reconnects and drains an empty inbox, and only then the worker writes the entry, which would sit unseen. To close this, the worker re-checks presence after every inbox write. If the user is now online, it sends a "nudge" to their gateway, which drains the inbox again (R7). |
| Reconnect drain interrupted | Entries are deleted only after the client acks them. The next connect resumes from what is left. |
| Inbox entry older than 30 days | The entry expires. The message remains in conversation history, and the client fills the gap by reloading history. |

## Assumptions

- The Message Store assigns `seq` inside the write transaction, and it can commit the message and outbox tables atomically. If it cannot, use its change-data-capture feed as the outbox instead.
- One device per user. Multiple devices would need an inbox per device.
- Live delivery order between different messages can still vary when a message is retried. Clients should render by `seq` and use the inbox drain to fill gaps.