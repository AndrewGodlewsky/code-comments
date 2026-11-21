## Message fan-out: online delivery and offline storage

This design covers a message from the moment the sender presses send until every recipient has it, whether or not they are connected.

Terms used throughout:
- **seq**: the per-conversation sequence number the Message Store assigns to each message.
- **msg_id**: an id the client generates for each message. It is how retries and duplicates are recognized.
- **heartbeat**: a small signal each client sends every 10 seconds over its WebSocket. A user counts as offline once 30 seconds pass without one. Each user has one device in this version.
- **Fan-out**: delivering one message to all of its recipients. The recipients are the conversation's members except the sender (at most 199).
- **At-least-once delivery**: a recipient may get the same message more than once, but never zero times. Clients drop duplicates by msg_id.

### Components

- **Gateway**: one of several nodes. Each client keeps one WebSocket open to one gateway. A gateway holds only live connections and no durable state.
- **Message Service**: validates a send, writes it to the Message Store, and acks the sender.
- **Message Store**: the existing conversation-history database. It assigns each message its seq and enforces a unique msg_id. It also holds an **outbox**, a table of rows meaning "this message still needs fan-out". A message and its outbox row are written in one transaction, so either both exist or neither does.
- **Outbox Relay**: reads unpublished outbox rows and publishes them to the Event Bus. It marks a row published only after the bus accepts it.
- **Event Bus**: a durable log partitioned by conversation id, so one conversation's messages are consumed in order.
- **Fan-out Worker**: consumes bus events and delivers each message to every recipient.
- **Presence Registry**: maps user id to the gateway holding that user's connection. Each heartbeat refreshes the entry, and an entry expires 30 s after the last heartbeat (its TTL, time to live).
- **Offline Inbox**: a per-user record of messages not yet confirmed delivered. Each entry holds the msg_id, conversation id and seq, not the message body. Entries expire after 30 days.
- **Push Service**: sends mobile push notifications.

### Diagram

```text
 SEND PATH (the sender waits only for steps 1-4)

 Sender --1 send(msg_id, text)--> Gateway A --2--> Message Service
                                                    |
                                  3 one transaction |
                                                    v
                                      +---------------------------+
                                      | Message Store             |
                                      |  messages (assigns seq)   |
                                      |  outbox   (needs fan-out) |
                                      +---------------------------+
 Sender <--4 ack(msg_id, seq)-- Gateway A <-- Message Service
                                (sent only after the commit)

 FAN-OUT PATH (asynchronous, off the sender's request path)

 Outbox Relay --5 read unpublished rows, publish--> Event Bus
      |          (partitioned by conversation id)       |
      |                                                 | 6 consume
      +-- 5b mark row published,                        v
          only after the bus accepts it          Fan-out Worker

   for each recipient (members except the sender):
     7  write entry to Offline Inbox (always, before trying delivery)
     8  look up recipient in Presence Registry
          online  --9a--> Gateway B --> recipient client
                          client acks within 5 s?
                            yes: 10a delete the Inbox entry
                            no:  leave the entry; treat as offline
                                 (then do 9b)
          offline --9b--> Push Service (best effort, one attempt)
   11 when every recipient is handled, commit the bus offset

 RECONNECT PATH

 Client --R1 connect--> Gateway
 Gateway --R2 read this user's entries--> Offline Inbox
 Gateway --R3 fetch message bodies--> Message Store
 Client <--R4 messages, in seq order per conversation-- Gateway
 Client --R5 acks--> Gateway --> delete the Inbox entries
```

### Flow in short

1. **Send.** The client sends a message with a client-generated `msg_id`. The Message Service writes the message and its outbox row in one transaction, and the Store assigns the seq. Only after the commit does the sender get `ack(msg_id, seq)`. No recipient is involved at this stage.
2. **Fan-out.** The Relay publishes the outbox row to the bus and then marks it published. A worker takes the event and handles each recipient, concurrently across recipients. For each one it writes an Inbox entry first, then tries delivery.
   - If the recipient is online, the message goes through their gateway. If the client's ack arrives within 5 s, the entry is deleted. Otherwise the entry stays, the recipient is treated as offline for this message, and the worker sends a push as in the next case.
   - If the recipient is offline, the worker sends one push and does not retry it.
   - The worker commits its bus offset only after every recipient has been handled.
3. **Reconnect.** The client connects. The gateway reads that user's Inbox entries, fetches the bodies from the Message Store, and sends them in seq order per conversation. The client acks them and the entries are deleted.

### Where state lives

| State | Where | Lifetime |
|---|---|---|
| Message and its seq | Message Store | permanent |
| "Needs fan-out" marker | outbox table, same transaction as the message | until the bus accepts it |
| Ordered event stream | Event Bus | until consumed |
| Who is online and on which gateway | Presence Registry | 30 s after the last heartbeat |
| Messages a recipient has not confirmed | Offline Inbox | until acked, at most 30 days |
| Seen message ids | each client | client-local, for deduplication |

### Failures

- **Store write fails.** The sender gets an error. No message or outbox row exists, so nothing is delivered. The client retries with the same `msg_id`. Because the Store enforces a unique `msg_id`, a retry never creates a second copy.
- **Crash after the commit, before the ack.** The message and outbox row are committed, so fan-out proceeds. The sender never sees the ack and retries with the same `msg_id`. The Store recognizes it, writes nothing new, and returns the original ack (same seq).
- **Relay or bus down, or crash after the commit.** The outbox row stays unpublished, and the Relay publishes it on recovery, so an acknowledged message is never lost. A crash between publishing and marking can publish a row twice. That is a duplicate, which clients drop.
- **Worker crashes mid-fan-out.** The bus offset was not committed, so another worker receives the event again. Inbox writes are keyed by (user, `msg_id`), so repeating them is harmless. Some recipients may get the message, or a push, twice. Clients drop the duplicate message by `msg_id`.
- **Recipient's ack times out (5 s).** The Inbox entry remains and the recipient is treated as offline for this message. A late ack still deletes the entry. If the client reconnects before that, it may receive the message again and drops the duplicate by `msg_id`.
- **Heartbeat missed (30 s).** The Presence entry expires and the user counts as offline. Fan-out skips the gateway and goes straight to the Inbox and push.
- **Gateway crashes.** Its connections drop and clients reconnect to another gateway. Its Presence entries expire by TTL. Anything unacked is still in the Inbox and is sent on reconnect.
- **Push fails.** The failure is logged and not retried. Push never touches the Inbox or the Store, so the message is still waiting at reconnect.
- **Inbox entry older than 30 days.** It expires. The message stays in the Message Store, so the client can still load it as ordinary history.
- **Ordering.** The bus keeps one conversation's events in order, and the worker handles them in order. But if a live delivery is lost or times out, a later message can arrive first. Each message carries its seq, so the client holds back or reorders by seq. Reconnect always returns messages in seq order.
- **Delivery guarantee.** Delivery is at-least-once. Duplicates are expected, and clients drop them by `msg_id`.