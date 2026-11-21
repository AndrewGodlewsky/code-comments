## Message fan-out

This design covers one chat message from the moment the sender presses send until every recipient has it, whether or not they are connected. It has three phases:

1. **Send**: the sender's request. The message is saved, and then the sender is acknowledged.
2. **Fan-out**: background delivery to every other member of the conversation. It never blocks the sender.
3. **Reconnect**: catch-up for recipients who were offline when the message arrived.

### Terms

- **seq**: a number that orders the messages in one conversation (1, 2, 3, and so on). Each conversation has its own sequence.
- **Acknowledgement (ack)**: a short reply that confirms receipt. The sender's ack means "the message is saved." A recipient's ack means "the message reached the device."
- **Outbox**: a table in the Message Store that lists messages still waiting to be announced to the rest of the system. Each outbox row is written in the same database transaction as its message. So a row exists only if its message was saved. This is the transactional outbox pattern. It prevents a saved message from being lost before fan-out starts.
- **Heartbeat and TTL (time to live)**: each client sends a heartbeat every 10 seconds. A record with a TTL is deleted automatically if nothing refreshes it before the TTL runs out.
- **At-least-once delivery**: a message may arrive more than once. Clients ignore repeats by message id.

### Components

- **Sender / Client**: the app on a user's device. It holds one WebSocket (a long-lived connection) to one Gateway node. It sends a heartbeat every 10 seconds.
- **Gateway**: a server node that holds client WebSockets. It forwards sends to the Message Service, pushes messages to connected clients, and forwards heartbeats to the Presence Registry.
- **Message Service**: handles a send. It writes the message and its outbox row in one database transaction.
- **Message Store**: the existing conversation history database. It holds messages, each with a seq, and the outbox table.
- **Outbox Relay**: reads outbox rows that have not been published yet and publishes them to the Event Bus.
- **Event Bus**: a queue split into partitions by conversation_id. Events for one conversation are processed in order.
- **Fan-out Worker**: takes one event per message and delivers it to each recipient. A conversation has at most 200 members and the sender is not a recipient, so there are at most 199 recipients.
- **Presence Registry**: records which Gateway node each online user is connected to.
- **Offline Inbox**: records, for each user, the messages that user has not yet received.
- **Push Service**: sends mobile push notifications.

```text
SEND (request path)

  Sender --(1) send msg_id + body--> Gateway --(2) forward--> Message Service
                                                                    |
                                                  (3) one transaction in Message Store:
                                                      - insert message, assign seq
                                                      - insert outbox row
                                                                    |
  Sender <--(4) ack msg_id + seq-- Gateway <------------------------+
            (sent only after the commit)


FAN-OUT (off the request path)

  Message Store outbox
        |  (5) Outbox Relay publishes unpublished rows
        v
  Event Bus (partitioned by conversation_id)
        |  (6) Fan-out Worker consumes the event
        v
  Fan-out Worker
        |  (7) for each recipient, read the Presence Registry
        |  (8) online: send through the recipient's Gateway,
        |      wait up to 5 s for the client's ack
        |  (9) offline, or no ack within 5 s: write an Offline Inbox entry
        |  (10) send a push notification (best effort, never retried)


RECONNECT

  Client --(11) connect--> Gateway --(12) set presence, TTL 30 s--> Presence Registry
    ^                         |
    |                         | (13) read the user's Offline Inbox entries
    |                         v
    +--(14) stream missed messages, bodies read from Message Store,
            ordered by conversation, then by seq.
            Each client ack removes the matching inbox entry.
```

### Where state lives

- **Messages and seq**: Message Store. Each message has a unique msg_id. If a send is retried with the same msg_id, the existing row is found and its msg_id and seq are returned. No second copy is created.
- **Outbox**: a table in Message Store, written in the same transaction as the message. A failed write leaves no outbox row. Every outbox row therefore belongs to a saved message. The relay marks a row as published after it has sent the row to the Event Bus.
- **Event Bus**: holds an event until the Fan-out Worker has finished with it. The worker commits its offset (its position in the queue) only after it has handled every recipient of that event.
- **Presence Registry**: one entry per user. This version assumes one device per user. The entry holds the Gateway node the user is connected to and expires 30 seconds after the last heartbeat. A user counts as online only while the entry exists. Entries are temporary and are rebuilt when clients reconnect.
- **Offline Inbox**: one entry per (user, message). Each entry holds conversation_id, seq and msg_id. It stores references only. Message bodies stay in Message Store. Entries expire after 30 days.
- **Client**: keeps the last seq it has for each conversation and the msg_ids it has already seen, so it can drop duplicates.
- **Push Service**: stores nothing.

### What happens on each failure

- **Message Store write fails**: the sender gets an error. No outbox row exists, so nothing is fanned out and no recipient gets anything. The client retries with the same msg_id.
- **Ack lost after the commit, or the sender retries**: the retry finds the saved message by msg_id and returns the original msg_id and seq. No duplicate is created.
- **Crash after the commit, before the ack is sent**: the outbox row survives, so fan-out still runs. The sender's retry gets the same ack.
- **Outbox Relay crashes**: unpublished rows stay in the outbox. When the relay restarts, it publishes them. A row can be published twice, and clients drop the duplicate.
- **Fan-out Worker crashes partway through an event**: the offset is not committed, so the whole event is delivered again. Recipients who already got the message receive it again and drop the duplicate. Inbox writes are keyed by (user, msg_id), so writing the same entry twice does no harm.
- **A live send gets no ack within 5 seconds**: the recipient is treated as offline for that message. The worker writes the inbox entry and sends the push. If the ack arrives late, the client holds the message twice and drops one copy. Recipients are handled in parallel, so one slow recipient does not delay the others.
- **A Gateway node dies**: its clients stop sending heartbeats, and their presence expires after 30 seconds. Until then, sends to them time out and fall back to the inbox. The clients reconnect to another node and sync.
- **Push fails**: the failure is logged and not retried. The inbox entry already exists, so the message still arrives on reconnect.
- **An inbox entry is older than 30 days**: the entry is deleted. The message stays in the conversation history in Message Store, but the reconnect catch-up no longer includes it.
- **The Presence Registry is lost or empty**: every user looks offline. Users receive inbox entries and pushes, and clients drop the duplicates during sync. This is safe but noisy.

### Open point

There is a race between reconnect and fan-out. A worker may read presence before a user reconnects, then time out on the live send and write an inbox entry after that user's reconnect sync has already run. That entry would then wait until the next reconnect. The fix, such as running a second sync shortly after connecting, is not yet decided.