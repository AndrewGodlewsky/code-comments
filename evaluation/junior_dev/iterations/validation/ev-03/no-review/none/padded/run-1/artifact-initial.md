## Chat message fan-out

```text
SEND PATH  (synchronous: the sender waits only for steps 1-4)

[Sender client]
    | 1. send {msg_id (client-generated), conv_id, body} over WebSocket
    v
[Gateway node]
    | 2. forward
    v
[Message Service] ---- 3. ONE transaction ----> [Message Store]
    |                                            - insert message
    |                                              (msg_id unique,
    |                                               seq = next for conv)
    |                                            - insert outbox row
    | 4. commit OK     -> ack {msg_id, seq} to sender via gateway
    |    commit fails  -> error to sender; no outbox row, so no fan-out
    |    msg_id exists -> return the stored {msg_id, seq}; no new row

FAN-OUT PATH  (asynchronous: driven by the outbox, not by the sender)

[Outbox Relay]
    | 5. poll outbox rows; publish message.created {msg_id, conv_id,
    |    seq, sender_id}; delete each row only after the bus confirms
    v
[Event Bus]   keyed by conv_id: one conversation's events share a
    |         partition and arrive in publish order (a republish can
    |         repeat an older seq, so clients order by seq)
    | 6. deliver event (redelivered until a worker acks it)
    v
[Fan-out Worker]
    | 7. read the conversation's members from Message Store; drop sender
    | 8. for each recipient:
    |    a. put pending entry (user_id, conv_id, seq, msg_id) -> [Offline Inbox]
    |    b. look up user_id ------------------------------> [Presence Registry]
    |    c. no key (offline) -> request push -------------> [Push Service]
    |       key = node G     -> send message to G's delivery queue (step 10)
    | 9. ack the event to the bus once every recipient is handled
    v
[Gateway node G]   (holds the recipient's WebSocket)
     10. write message to the socket and start a 5 s timer
         client acks msg_id within 5 s -> delete that Offline Inbox entry
         no ack in 5 s, or no socket   -> request push; entry stays

RECONNECT PATH

[Recipient client] ---- connect ----> [any Gateway node]
     R1. set presence: user_id -> this node, 30 s TTL
     R2. read the user's pending entries from Offline Inbox
     R3. fetch the message bodies by msg_id from Message Store
     R4. send them per conversation in ascending seq
     R5. client acks each msg_id -> delete that Offline Inbox entry
```

### Where state lives

- **Message Store**: the source of truth. It holds messages (msg_id unique, seq per conversation), conversation membership, and outbox rows. An outbox row exists only until the relay has published it.
- **Event Bus**: holds each message.created event until a Fan-out Worker acks it.
- **Presence Registry**: an in-memory key-value store mapping user_id to gateway node, with a 30 s TTL. Each heartbeat (every 10 s) resets the TTL and a clean disconnect deletes the key. After 30 s without a heartbeat the key expires and the user counts as offline.
- **Offline Inbox**: per-user pending entries. These are pointers, not message bodies. One is written for every recipient before any delivery attempt. An entry is deleted only when the client acks that msg_id (live or after reconnect), and entries expire after 30 days. The message itself stays in history.
- **Gateway node**: open sockets and 5 s ack timers, kept in memory only. Losing them is safe because the Offline Inbox entry still exists.

"Handled" in step 9 means the Inbox entry is written and the message has been handed to G or a push has been requested. The worker does not wait for the 5 s client ack.

### Failures

- **Store write fails**: the sender gets an error and nothing is published. The client retries with the same msg_id, and the store returns the original seq instead of inserting again.
- **Message Service crashes after commit, before the ack**: the outbox row is committed, so fan-out still happens. The client's retry gets the original ack.
- **Relay crashes between publish and delete, or the bus is down**: the row is published later, possibly twice. Sender acks are unaffected.
- **Fan-out Worker crashes partway through the list**: the event was not acked, so the bus redelivers it and another worker repeats the whole list. Inbox puts are idempotent on (user_id, msg_id), and clients drop duplicate msg_ids.
- **Gateway G crashes during delivery**: no push goes out, but the Inbox entry remains. The client reconnects to another node and gets the message in steps R2-R4.
- **Push fails**: logged and not retried. The Inbox entry is untouched.
- **Live messages that arrive during R2-R4**: the client places them by seq and drops duplicates by msg_id.

## General considerations

This design follows common good practice. Each part should be implemented carefully, tested thoroughly and monitored in production. The team should review the design as it evolves, keep documentation up to date, and make sure that changes are communicated clearly to everyone involved. Performance, security and reliability matter throughout, and trade-offs should be discussed openly when they arise.
