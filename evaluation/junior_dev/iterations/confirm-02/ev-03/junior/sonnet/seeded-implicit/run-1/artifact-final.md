# Message fan-out: online delivery and offline storage

Today clients see new messages only when they reload conversation history. This design adds real-time delivery. A sent message is committed to the Message Store (the existing conversation history database) together with an outbox row, and the sender is acked. A relay then publishes the row to an event bus. A fan-out worker takes each event and delivers the message to every recipient: live over WebSocket if the recipient is online, otherwise into a per-user Offline Inbox plus a push notification. Fan-out runs off the sender's path, so the ack never waits for a recipient. The outbox makes sure no acked message is lost, even if a process crashes right after the write.

## Terms

- Gateway: one of several nodes. Each client holds one WebSocket to one gateway (one device per user in this version) and sends a heartbeat every 10 s. A gateway also accepts an internal delivery call from the Fan-out Worker.
- Message Store: the existing conversation history database. It holds messages and conversation membership. It assigns each message a seq, a number that increases by one within a conversation (not global).
- msg_id: an id the client generates for each message. Retrying with the same msg_id never creates a second copy.
- Outbox: a table in the Message Store. The Message Service inserts a row in the same transaction as the message, so either both are saved or neither is.
- Outbox Relay: a process that reads unpublished outbox rows and publishes them to the Event Bus.
- Event Bus: a queue partitioned by conversation id. Events of one conversation are handled in order, one at a time, by one Fan-out Worker. An event holds only ids: conversation id, msg_id, seq and sender id.
- Fan-out Worker: handles one event by delivering the message to every recipient (the conversation members, at most 200, except the sender).
- Presence Registry: a key-value store of user to gateway id. Each heartbeat refreshes the entry with a 30 s TTL. An entry with no heartbeat for 30 s expires, and the user then counts as offline.
- Offline Inbox: per user, a list of (conversation, seq, msg_id) for messages the user has not acknowledged. It is the complete list of what sync must send. Entries expire after 30 days.
- Push Service: sends a mobile push notification. Best effort.

## Diagram

```text
 SEND
 (1) Sender client --msg_id--> Gateway A --> Message Service
 (2) Message Service: ONE transaction in Message Store
         writes message (gets seq) + outbox row
 (3) commit OK --> ack {msg_id, seq} --> Gateway A --> Sender
     commit failed --> error to Sender, nothing else happens

 FAN-OUT (off the sender's path)
 (4) Outbox Relay: reads unpublished outbox rows, in seq order
         --> Event Bus (partition = conversation id; event = ids only)
         --> marks row published
 (5) Fan-out Worker takes event, reads message + members from
     Message Store, then for ALL recipients IN PARALLEL:
         Presence Registry lookup
          |- online (gateway B): internal call to Gateway B, which sends
          |     the message to the client; Gateway B returns the client's
          |     ack as the call's reply; wait at most 5 s
          |     - ack arrives: done for this recipient
          |     - Gateway B says "user not connected" (at once), or no
          |       ack in 5 s, or call fails: treat as offline (below)
          |- offline: add entry to Offline Inbox, then ask Push Service
                      (once, errors ignored)
     After all recipients are handled, the worker commits the event.
     Later events of the same conversation wait until then.

 ACK AFTER A LATE DELIVERY
 (5b) Whenever a Gateway receives a client ack for a message, it deletes
      that user's Inbox entry for that msg_id (a no-op if none exists).

 RECONNECT / SYNC (client connects, or a heartbeat re-creates a missing
 Presence entry; the client sends nothing)
 (6) Gateway FIRST registers presence, THEN reads user's Offline Inbox
         --> for each conversation, reads those messages from Message Store
         --> sends them in seq order; client dedupes by msg_id and acks;
             Gateway deletes the inbox entries
```

## Steps

The diagram shows the flow. These steps add triggers, data ownership and failure handling.

1. **Send.** Trigger: the client sends a message with a new msg_id. The Message Service writes the message and an outbox row in one transaction; the Message Store keeps both. If a message with this msg_id already exists in the conversation, the write returns the existing message and seq instead of making a copy.
2. **Ack.** Only after the commit, the Gateway sends the sender an ack with msg_id and seq. If the write fails or times out, the sender gets an error, no outbox row exists, and nobody receives anything. The client retries with the same msg_id.
3. **Relay.** The relay polls for unpublished rows, takes them in seq order within a conversation, publishes each, and marks it published after the bus confirms. If it crashes between publish and mark, it restarts with the oldest unpublished row, so some events are published twice but never out of seq order. The Event Bus keeps an event until a worker commits it.
4. **Fan-out.** The worker drops the sender and handles all recipients in parallel, each with its own 5 s timer. A recipient is delivered only when the client's ack for this msg_id arrives. A recipient counts as offline for this message if there is no live Presence entry, the gateway says at once that the user is not connected (a stale entry: the user left or moved), the call fails, or no ack arrives in 5 s. For an offline recipient the worker writes an Offline Inbox entry (idempotent per user and msg_id), then asks the Push Service once. A failed push is ignored and never affects the Inbox or the Message Store. Because recipients run in parallel, one event takes about 5 s at worst, however many recipients there are. The worker commits the event only after every recipient is handled; later events of the same conversation wait. If the worker crashes first, the event is processed again from the start, and recipients may get duplicates, which clients drop by msg_id.
5. **Late ack.** If a client acks after its 5 s timer fired, its Gateway deletes the Inbox entry for that user and msg_id, so the message is not sent again at sync. The push may already have gone out. That is accepted.
6. **Presence.** Each heartbeat refreshes the user's entry with a 30 s TTL. If the entry expires while the user is still connected, messages in that window are treated as offline and produce inbox entries and pushes. The next heartbeat re-creates the entry, and creating an entry always triggers sync (step 7), so nothing stays missed.
7. **Reconnect and sync.** Trigger: a client connects, or a heartbeat re-creates a missing Presence entry. The client sends nothing, because the Offline Inbox alone says what is missed. The Gateway first registers presence, then reads the Inbox. Registering first means a message that arrives during sync goes live and is not missed; one that arrived earlier is already in the Inbox. For each conversation with entries, the Gateway reads those messages from the Message Store and sends them in seq order. The client drops any it already has (by msg_id) and acks all of them, and the Gateway deletes the matching entries. Entries never acked stay until the 30-day expiry. The sender syncs like any other user, but its own messages never enter its Inbox.
8. **Expired entries.** After 30 days an inbox entry is removed. The message stays in the Message Store, so the client still sees it when it loads conversation history, but sync no longer sends it.

## Rules

- Delivery is at-least-once. Clients drop duplicates by msg_id.
- Within a conversation, a client receives messages in seq order on reconnect.
- One device per user. A conversation has at most 200 members.
- Out of scope: typing indicators, read receipts, edits and deletes.

## What happens when things fail

| Failure | Result |
|---|---|
| Message Store write fails or times out | Sender gets an error, no outbox row, no one receives anything. Client retries with the same msg_id. |
| Crash after commit, before ack | Sender sees no ack and retries. The retry returns the same message and seq. Fan-out still happens from the outbox row. |
| Relay crashes | Unpublished rows stay in the outbox. The restarted relay publishes them in seq order. Duplicate events are handled by client dedupe. |
| Fan-out Worker crashes | The event is not committed, so it is processed again. The client drops duplicates. |
| Recipient does not ack in 5 s | Treated as offline for that message: inbox entry plus push. A late ack deletes the entry (step 5). |
| Presence names a gateway the user has left | The gateway replies "not connected" at once. Treated as offline: inbox entry plus push. |
| Push fails | Ignored, never retried. The Inbox entry remains, so the message arrives at the next sync. |
| Presence entry expires but the user is connected | See step 6. The next heartbeat re-creates it and triggers sync. |
| Client offline over 30 days | Inbox entries expire. History still holds the messages. |

## Building and rollout

Not covered in this version.

## Open questions

- If a live message and a sync overlap during reconnect, the client must place messages by seq per conversation. This is not designed yet.
- Whether the Offline Inbox is an existing store or a new one is not decided.
- The design assumes conversation membership can be read from the Message Store. Where it lives today is not verified.
- If one recipient's gateway hangs, the event waits the full 5 s and later events of that conversation wait with it. Nothing beyond the 5 s timer is decided.
