# Message fan-out

Today clients see a new message only when they reload conversation history. This design adds real-time delivery on top of the existing Message Store, which stays the source of truth. The sender waits only for the durable write. Recipients are reached afterwards through an outbox, so an acknowledged message still reaches everyone if a process crashes. Every step can safely run twice, because delivery is at-least-once and clients drop duplicates.

Scope: one device per user. A conversation has at most 200 members, and the sender is never a recipient of their own message. Typing indicators, read receipts, edits and deletes are out of scope.

## Terms

- **Gateway node**: a server that holds a client's WebSocket. There are several.
- **WebSocket**: a connection that stays open, so the server can push messages to the client.
- **Heartbeat**: a small message the client sends every 10 seconds to say it is still connected.
- **Message Store**: the existing conversation history database. It gives each message its sequence number.
- **Sequence number (seq)**: a number per conversation that gives its messages their order.
- **msg_id**: a unique id the client makes for each message. A retry sends the same msg_id.
- **Ack**: a short reply that confirms something arrived.
- **Outbox**: a row written in the same database transaction as the message. It says "this message still needs fan-out."
- **Outbox Relay**: a process that reads outbox rows and publishes them to the Event Bus.
- **Event Bus**: a message queue, partitioned by conversation so one conversation's events stay in order.
- **Fan-out Worker**: a process that takes one event and delivers it to each recipient.
- **Presence Registry**: a store of which users are online. A user's entry expires 30 seconds after their last heartbeat.
- **Offline Inbox**: a per-user list of messages not yet delivered. Entries expire after 30 days.
- **Push Service**: sends mobile push notifications.
- **At-least-once**: a message may arrive more than once, but it arrives at least once.
- **Idempotent**: repeating a request gives the same result, with no extra copy.

## Diagram

```text
SEND
 (1) Sender --send(msg_id, text)--> Gateway --> Message Service
 (2) Message Service --one transaction--> Message Store
        writes: message + seq + outbox row
 (3) Message Service --ack(msg_id, seq)--> Gateway --> Sender

FAN-OUT (not on the sender's request path)
 (4) Outbox Relay --reads outbox row--> Event Bus (partitioned by conversation)
 (5) Fan-out Worker, for each recipient except the sender:
        Presence Registry says online?
          yes --> Gateway --> client --ack within 5 s--> done
          no, or no ack in 5 s --> Offline Inbox
 (6) Push Service (best effort, never retried)

RECONNECT
 (7) Client opens a WebSocket to a Gateway node; heartbeats keep it online
 (8) Gateway reads the user's Offline Inbox, loads those messages from
     Message Store, and sends them in seq order within each conversation;
     client acks each one
```

## Notes on the steps

1. **Send.** The user presses send. The client keeps the message and its msg_id until it gets the ack. Nothing is stored on the server yet.
2. **Write.** The Message Service writes the message, its seq and an outbox row in one transaction. If the msg_id already exists, it returns the existing seq and writes nothing. Message text is kept in the Message Store.
3. **Ack.** The Message Service acks the sender only after the commit. The ack does not wait for any recipient.
4. **Relay.** The Outbox Relay publishes each outbox row to the Event Bus and marks the row published. Events for one conversation stay in order because they share a partition.
5. **Fan-out.** The Fan-out Worker handles each recipient, up to 199 per message. For an online recipient, it sends the message through the gateway and waits up to 5 seconds for the client's ack. For an offline recipient, or one with no ack in 5 seconds, it adds the message to that user's Offline Inbox. The 5-second rule applies to that one message only; the user stays online for later messages. The worker marks the event done only after every recipient is handled. The Presence Registry keeps online state, refreshed by heartbeats. The Offline Inbox keeps one entry per undelivered message, with a reference to the message in the Message Store.
6. **Push.** The Push Service sends a mobile push to each offline recipient. Push is best effort and is never retried. Its result never changes the Offline Inbox or the Message Store.
7. **Connect.** The client opens a WebSocket to a gateway node. Heartbeats keep its presence entry alive.
8. **Sync.** The gateway reads the user's Offline Inbox, loads those messages from the Message Store and sends them in seq order within each conversation. The client drops any duplicate by msg_id. Any ack for a message removes that user's inbox entry for it. An entry stays until acked, so a disconnect during sync is safe: the rest is sent on the next reconnect.

## What happens when things fail

| What goes wrong | What happens | Why nothing is lost or doubled |
|---|---|---|
| The Message Store write fails | The sender gets an error. Nothing is stored and no one receives anything. | The client retries with the same msg_id. |
| The write commits but the ack never reaches the sender | The sender sees no ack. | The retry returns the existing seq. No second copy is written. |
| A process crashes after the commit but before the relay publishes | The outbox row stays unpublished. | The relay publishes it later, so fan-out still happens. |
| The relay publishes but crashes before marking the row | The event is published twice. | Fan-out runs twice. Clients drop the duplicate. |
| The Fan-out Worker crashes mid-event | The event is not marked done. | The bus redelivers it until the worker finishes. Some recipients may get the message twice. Clients drop duplicates. |
| Writing to a recipient's Offline Inbox fails | The event is not marked done. | The event is redelivered and the recipient is handled again. |
| A gateway node dies | Its clients disconnect and their heartbeats stop. They count as offline 30 seconds later. | Clients reconnect to another node. Sync sends what they missed. |
| An online client does not ack within 5 seconds | The message goes to the Offline Inbox and a push is sent. | A late ack removes the inbox entry. A repeat delivery is dropped by msg_id. |
| The push fails or times out | Nothing is retried. | The inbox entry stays, so the client still gets the message on reconnect. |
| A sync is interrupted | Unacked entries remain. | They are sent again on the next reconnect. |
| A user is offline for more than 30 days | Their inbox entries expire and are not sent on reconnect. | The messages still exist in the Message Store (see open questions). |

## Open questions

- The brief does not say how long the Message Store keeps message text. The 30-day inbox promise only works if it keeps text for at least 30 days.
- The brief does not say how a long backlog is sent on reconnect, such as in pages or with size limits.