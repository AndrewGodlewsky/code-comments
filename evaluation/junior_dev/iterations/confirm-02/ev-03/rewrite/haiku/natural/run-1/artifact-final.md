## Chat message fan-out: online delivery and offline storage

Today clients see new messages only after they reload conversation history. This design adds live delivery: a sent message is saved first and the sender is acknowledged, then a background worker delivers it to every other member of the conversation. Online members receive it over their open connection. Offline members find it waiting in a mailbox when they reconnect, and get a best-effort push notification.

Out of scope: typing indicators, read receipts, edits and deletes.

### Terms

- **Message Store**: the existing database that holds conversation history. It is the authoritative copy of every message. How long history is kept is outside this design.
- **seq**: a number that orders messages within one conversation (1, 2, 3...). It is given when the message is saved.
- **message_id**: an id the client makes for each message. A retry reuses it, so the server can tell a retry from a new message.
- **Row lock**: the database holds the conversation's row during a send, so two sends cannot take the same seq.
- **Gateway node**: a server that holds open WebSocket connections to clients. There are several.
- **WebSocket**: a connection kept open between a client and a gateway node. Each message sent over it is a **frame**.
- **Heartbeat**: a ping that a connected client sends every 10 seconds.
- **Presence store**: a fast key-value store (Redis or similar). For each user it holds the key `presence:{user_id}` with `{gateway_node, connection_id}` and a 30-second TTL, refreshed by each heartbeat. A missing key means offline, which is what happens after 30 seconds without a heartbeat. This version assumes one device per user: a new connection overwrites the key and closes the old socket.
- **Fanout outbox**: a table in Message Store with one row `(conv_id, message_id, seq)` per saved message that still needs fan-out. It is written in the same transaction as the message, so every acknowledged message has a row.
- **Relay**: the process that reads the fanout outbox and passes rows to the fan-out worker, in seq order within each conversation. How it reads is open (see the end).
- **Fan-out worker**: the background process that writes mailbox rows, sends live frames and sends pushes.
- **Mailbox**: a table, in Message Store or a sibling table, with one row per recipient per message not yet acked: `(user_id, message_id, conv_id, seq, created_at)`, keyed by `(user_id, message_id)`. Rows expire 30 days after `created_at`. TTL (time to live) means the database deletes the row automatically after that time. Only the fan-out worker writes to it.
- **Push**: a mobile notification sent through an outside push provider. Its payload is only a wake-up hint. The provider stores nothing from this design.
- **Ack**: a confirmation message. The server acks the sender after the save. Each online client acks each frame it receives.
- **Client state**: each client keeps the last seq it has seen per conversation and a set of recent message ids, to drop duplicates.
- **At-least-once**: a message may arrive more than once, but never fewer than once. Clients drop duplicates by message_id.

### Diagram

```
 SEND PATH (sender waits for this only)

 Sender ──1. send {message_id, conv_id, body}──► Gateway A
                                                   │
                                                   │ 2. DB transaction (Message Store):
                                                   │    a. lock conversation row
                                                   │    b. look up message_id in conv; if found, skip to d
                                                   │    c. seq = conversation.next_seq + 1; insert message;
                                                   │       insert fanout_outbox row; commit
                                                   │    d. return existing or new (message_id, seq)
                                                   ▼
 Sender ◄──3. ack {message_id, seq}────────────── Gateway A
        (on any failure in 2: error, nothing written, nothing fanned out)


 FAN-OUT PATH (async, never on the sender's request path)

 Message Store                 4. relay reads fanout_outbox (poll or CDC),
 fanout_outbox ───────────────► partitioned by conv_id, in seq order
                                       │
                                       ▼
                               Fan-out worker
                                       │ 5. load members (<= 200), drop sender
                                       │ 6. for each recipient: upsert Mailbox row
                                       │    key (user_id, message_id), TTL 30 days
                                       │ 7. read Presence store: user_id → node, live if key exists
                                       │
                     ┌─────────────────┴──────────────────┐
                     ▼ 8a. live (node known)              ▼ 8b. offline, or no ack in 5 s
              Gateway B ──frame──► Recipient        Push provider (best effort, one attempt)
                     │
                     │ 9. recipient acks message_id within 5 s
                     ▼
              delete Mailbox row (user_id, message_id)

              10. when every recipient has a Mailbox row and a live attempt has been started,
                  delete the fanout_outbox row


 RECONNECT PATH

 Recipient ──11. WS connect + auth──► Gateway C
                                        │ 12. presence key set with 30 s TTL;
                                        │     client heartbeat every 10 s refreshes it
                                        │ 13. read Mailbox WHERE user_id
                                        │     ORDER BY conv_id, seq
                                        │ 14. send frames in that order
 Recipient ◄──────────────────────────── │
 Recipient ──15. ack each message_id──► delete Mailbox row
   16. client drops duplicates by message_id, delivers each conversation in seq order
   17. a seq gap inside a conversation triggers a sync request for seq > last,
       answered from Message Store history
```

### Steps

The diagram shows the flow. These steps add the trigger, the part that keeps each piece of data, and what happens when a step goes wrong.

**Send path.** The sender waits for steps 1 to 3 only.

1. **Trigger:** the sender presses send. The client sends `{message_id, conv_id, body}` to its gateway node. The client keeps the message_id until it gets an ack.
2. **The gateway runs one transaction in Message Store.** It locks the conversation row, then looks up message_id in that conversation. If the message is already there, it skips to the return. Otherwise it sets seq to `conversation.next_seq + 1`, inserts the message, inserts the fanout outbox row, sets `next_seq` to the new value and commits. It then returns `(message_id, seq)`. A retry finds the committed row and returns the same pair, so no second copy is created.
   - *If it fails:* the transaction rolls back, so no message, seq or outbox row exists. The sender gets an error, nothing is received by anyone, and the client retries with the same message_id.
3. **The gateway acks the sender** with `{message_id, seq}` after the commit. The sender does not wait for any recipient.
   - *If the ack is lost, or the server crashes after the commit:* the outbox row is durable, so fan-out still runs. The client's retry gets the same `(message_id, seq)` from step 2.

**Fan-out path.** Runs in the background and never on the sender's request path.

4. **Trigger:** a new fanout outbox row. The relay reads rows partitioned by conv_id, in seq order. The row stays until step 10.
   - *If the relay stops:* the rows remain and are read again when it restarts.
5. **The worker loads the conversation's members** (at most 200) and drops the sender. Membership is read now, at fan-out time, not at send time. That leaves at most 199 recipients, so each message causes at most 199 mailbox upserts and at most 199 pushes, all in the worker.
6. **For each recipient, the worker upserts a mailbox row** keyed by `(user_id, message_id)`, with a 30-day TTL. Repeating an upsert changes nothing.
   - *If the worker crashes here:* the outbox row is still there, so step 4 runs the message again.
7. **The worker checks presence** for each recipient. A recipient is live if its presence key exists, and the key names the gateway node to use.
8. **Delivery:**
   - **8a, live:** the worker sends a frame through the recipient's gateway node and waits up to 5 seconds for the ack. Frames to one recipient go out in seq order on that socket. Each recipient has its own 5-second timer, so a slow recipient does not hold up the conversation.
   - **8b, offline, or no ack within 5 seconds:** the worker makes one push attempt. Nothing is retried.
   - *If the socket drops or the ack is lost:* the recipient counts as offline for that message, so 8b runs. The mailbox row stays.
   - *If the push fails or times out:* it is logged and dropped. It never changes the mailbox, the outbox or Message Store.
9. **The recipient acks the message_id** within 5 seconds of the frame. The ack deletes the mailbox row. A late ack still deletes it.
10. **When every recipient has a mailbox row and a live attempt has started, the worker deletes the outbox row.**
    - *If the worker crashes before this:* step 4 runs the message again. A duplicate live frame is possible; clients drop it.

**Reconnect path.** Runs when a recipient connects again.

11. **Trigger:** the recipient opens a WebSocket to a gateway node and connects.
12. **The gateway sets the presence key** with a 30-second TTL. Heartbeats refresh it every 10 seconds.
13. **The gateway reads the user's mailbox rows,** ordered by `conv_id`, then `seq`.
14. **The gateway sends the frames in that order.** A live frame may arrive while the replay runs, so the client must handle overlap.
15. **The client acks each message_id.** Each ack deletes its mailbox row. A message that is never acked stays in the mailbox and is sent again on the next reconnect.
16. **The client drops duplicates by message_id** and delivers each conversation in seq order.
17. **A seq gap inside a conversation** (for example, seq 5 went to the mailbox while seq 6 arrived live) makes the client send a sync request for seq greater than its last seq. Message Store history answers it. Delivery of the live stream does not wait for the gap.

### What happens when things fail

This table covers failures that involve more than one part. Failures at a single step are in the steps above.

| What fails | What happens | Where the data is |
|---|---|---|
| Gateway node dies | Its presence keys expire within 30 seconds, so its users count as offline. They reconnect to another node and drain the mailbox. Frames in flight are covered by mailbox rows that were never acked. | Mailbox rows |
| Presence store is unavailable | The worker cannot tell who is online. It still writes mailbox rows, so delivery stays durable. It skips live frames and pushes, because offline status cannot be confirmed. Recipients catch up on reconnect. Push coverage has a known gap for the length of the outage. | Mailbox rows, outbox |
| An online recipient's ack times out | The recipient counts as offline for that message. It may get both a live frame and a push, which is accepted under at-least-once delivery. The row is replayed on reconnect, and the client drops the duplicate. | Mailbox row |
| A mailbox row passes its 30-day TTL before the recipient reconnects | The row is purged. The client sends a sync request with its last seq per conversation and recovers from history. | Message Store history |
| Membership changes between send and fan-out | The worker reads members at fan-out time. A member added after the send may receive the message, and a member removed may not. | Conversation membership |

### Open questions

- The relay mechanism is not fixed. It may poll the outbox table, or use change data capture (CDC), which streams database changes.
- The presence store technology is not fixed. Redis, or a database table with a TTL column, are both options.
- Pushes for ack timeouts: this design sends them both to timed-out online recipients and to confirmed offline ones. That trades duplicate notifications against missed ones. The choice is not made.
- How clients authenticate on connect, and what happens when that fails, is not specified.