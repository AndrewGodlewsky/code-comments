## Message fan-out

Today clients see new messages only when they reload conversation history. This design adds real-time delivery. A message is first written durably to the Message Store (the conversation history database) together with an outbox record, and the sender is acked. A background pipeline then reads the outbox and delivers the message to each recipient: straight to their open WebSocket if they are online, or into a per-user Offline Inbox plus a mobile push notification if they are not. The write and the outbox record commit together so that an acked message can never be lost, and fan-out stays off the sender's request path.

### Terms

- **Gateway**: one of several nodes. Each client holds one WebSocket to one gateway. Assume one device per user.
- **Message Service**: validates and stores a sent message. It is the only writer to the Message Store on the send path.
- **Message Store**: the existing conversation history database. It gives each message a per-conversation sequence number (seq). Messages are unique by the client-generated message id (msg_id).
- **Outbox**: a table in the Message Store. A row is added in the same commit as the message, and says "this message still needs fan-out".
- **Outbox Relay**: a process that publishes unpublished outbox rows to the Event Bus, then marks them published.
- **Event Bus**: a durable queue, partitioned by conversation id, so the messages of one conversation are handled in order. It delivers at-least-once.
- **Fan-out Worker**: reads bus events and delivers each message to the conversation's recipients (all members except the sender; at most 200 members).
- **Presence Registry**: a key per user (which gateway they are on) with a 30 second TTL. Each client heartbeat, every 10 s, renews it. A user is offline once 30 s pass with no heartbeat.
- **Offline Inbox**: per recipient, the list of messages (msg_id and seq) they have not confirmed. Entries expire after 30 days.
- **Push Service**: sends a mobile push notification. Best effort.

### Diagram

```text
 SEND (sender request path)
   Sender --1 send(msg_id)--> Gateway --2--> Message Service
   Message Service --3 one commit: message + seq + outbox row--> Message Store
   Message Service --4 ack(msg_id, seq)--> Gateway --> Sender
        (write fails: error to sender, nothing stored, nothing sent)

 FAN-OUT (background, after the ack)
   Outbox Relay --5 read unpublished rows--> Message Store
   Outbox Relay --6 publish, key = conversation id--> Event Bus
   Outbox Relay --7 mark row published--> Message Store
   Event Bus --8 event--> Fan-out Worker
   For each recipient:
     Fan-out Worker --9 where is user?--> Presence Registry
       online : --10 deliver--> Gateway --> Recipient client
                client acks within 5 s -> done
                no ack in 5 s          -> treat as offline (below)
       offline: --11 add entry--> Offline Inbox
                --12 best-effort push--> Push Service

 RECONNECT
   Client --13 connect, heartbeat--> Gateway --> Presence Registry
   Gateway --14 read entries--> Offline Inbox
   Gateway --15 load bodies--> Message Store
   Gateway --16 send, sorted by seq per conversation--> Client
   Client acks -> entries removed from Offline Inbox
```

### Steps

1. **Send (1-4).** The client sends a message with its own msg_id. The Message Service writes the message, its seq and the outbox row in one commit. Only then does it ack the sender, with msg_id and seq. If the write fails, the sender gets an error and no one receives anything. The client retries with the same msg_id. The Message Store sees the existing msg_id and returns the original seq instead of creating a second copy.
2. **Relay (5-7).** The relay runs continuously. It publishes each unpublished outbox row to the bus, then marks it published. If the relay crashes between publish and mark, the row is published again; this is allowed because delivery is at-least-once. If the bus is down, rows stay unpublished and the relay retries.
3. **Fan-out (8-9).** The worker takes an event and looks up each recipient in the Presence Registry. It finishes the event only after every recipient has either been acked or been given an inbox entry. If the worker crashes first, the bus redelivers the event. If the Presence Registry cannot be reached, the worker treats the recipient as offline, which is safe because the inbox entry is delivered on reconnect.
4. **Online recipient (10).** The worker asks the recipient's gateway to send the message. The client acks each message it receives. If no ack arrives within 5 s (client gone, gateway crashed, connection stalled), the worker treats the recipient as offline for that message.
5. **Offline recipient (11-12).** The worker adds an entry to the recipient's Offline Inbox, kept up to 30 days, then asks the Push Service to send a notification. Push is never retried, and a failed push never affects what is stored. If the inbox write fails, the worker does not finish the event, so the bus redelivers it. After 30 days, expired entries are gone; the message is still in the Message Store history.
6. **Reconnect (13-16).** The gateway reads the user's inbox entries, loads the message bodies from the Message Store, and sends them in seq order within each conversation. Entries are removed as the client acks them. If the connection drops part way, the remaining entries stay and are sent next time.

### Rules for all steps

- Delivery may be at-least-once. Clients drop duplicates by msg_id. Retries and redeliveries are therefore always safe.
- The sender is never a recipient of their own message.
- State lives in: the Message Store (messages, seq, outbox), the Event Bus (events not yet processed), the Presence Registry (who is online, expires on its own), the Offline Inbox (what each user has missed).

### Failure summary

| What fails | What happens |
|---|---|
| Message write | Sender gets an error, nothing stored or sent; client retries with the same msg_id. |
| Crash right after the write | Outbox row is committed, so the relay still publishes it. No message is lost. |
| Relay crash | Unpublished rows are picked up again; duplicates are dropped by clients. |
| Worker crash | Bus redelivers the event; duplicates are dropped by clients. |
| No client ack in 5 s | Recipient treated as offline for that message: inbox entry and push. |
| Push fails | Ignored; nothing is retried or changed in storage. |
| Gateway crash | Its clients reconnect and receive their missed messages from the inbox. |

### Open questions

- None known. Not decided here: how the inbox removes an entry for a message that was acked online after an earlier timeout; clients dedupe by msg_id, so a duplicate is harmless.