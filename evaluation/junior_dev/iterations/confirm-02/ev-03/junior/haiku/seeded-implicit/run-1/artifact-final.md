## Message fan-out

Today, clients see a new message only when they reload conversation history. This design adds live delivery on the same Message Store. A send is saved and acknowledged first. A background fan-out then records one Offline Inbox row per recipient and tries live delivery. A recipient who is offline, or does not acknowledge within 5 seconds, gets a push and collects the message when it reconnects. The sender waits only for the database write, so once it has its ack the message is stored. The design aims to reach every recipient; one gap is listed under open questions.

### Rules

- Each user has one device, so presence and the inbox are kept per user.
- A conversation has at most 200 members. The sender is never a recipient of their own message, so one send reaches at most 199 people.
- Delivery is at-least-once. A message can arrive more than once, and clients drop the extra copies by msg_id.
- Undelivered messages are kept for up to 30 days.
- Out of scope: typing indicators, read receipts, edits and deletes.

### Terms

- **Message Store**: the existing conversation history database. It holds messages, seq numbers, conversation members and the outbox.
- **Message Service**: the server that handles a send and writes it to the Message Store.
- **msg_id**: an id the sender's client makes once per message and reuses on every retry.
- **seq**: a number per conversation that the Message Store gives each message when it is saved. It is the order of record.
- **Outbox**: a table in the Message Store with one row per saved message that is not yet published to the Event Bus.
- **Outbox Relay**: the process that moves outbox rows onto the Event Bus.
- **Event Bus**: a queue of 'message saved' events, split into partitions by conversation id. A partition is one ordered lane of the bus, and one conversation's events stay in one partition. Each event carries only ids: conversation id, seq, msg_id and sender id. It never carries the message text.
- **Fan-out Worker**: the process that takes one bus event and delivers it to each recipient.
- **Gateway**: a server node that holds its clients' WebSocket connections. There are several. A WebSocket is a connection that stays open between a client and a server.
- **Heartbeat**: a short message a client sends every 10 seconds to show it is still connected.
- **Ack**: a reply saying a message was received. Clients ack each message they receive.
- **Presence Registry**: a store with one entry per user. The entry names the gateway that holds the user's connection. It expires 30 seconds after the last heartbeat. It is rebuilt by heartbeats and is not durable.
- **Offline Inbox**: a table with one row per user per message, holding user, conversation, seq, msg_id and a delivered flag. Rows stay after delivery, so a repeated fan-out cannot make a new copy. Rows expire after 30 days.
- **Push Service**: the service that sends mobile push notifications.

### Diagram

```text
SEND (on the request path)
Sender client --msg_id, text--> Gateway --> Message Service
                                              |  1 save in one Message Store transaction:
                                              |    - insert message (store assigns seq)
                                              |    - insert outbox row
                                              |    - COMMIT
Sender client <--msg_id, seq--- Gateway <-----+  2 ack, only after commit

FAN-OUT (background, off the request path)
Message Store outbox --> 3 Outbox Relay --> Event Bus (partition = conversation;
                                             event = ids only)
                                                  |
                                                  v
                              4 Fan-out Worker, one event at a time per partition:
                                - load message text once from Message Store
                                - load members from Message Store, minus sender
                                - for each recipient, in parallel:
                                  a) insert Offline Inbox row if none exists;
                                     stop if the row is already delivered
                                  b) read Presence Registry (online? which gateway?)
                                  c) if online: Gateway sends text to client;
                                     client acks; Gateway marks row delivered,
                                     then reports the ack to the worker;
                                     worker waits up to 5 s for that report
                                  d) if offline, send failed, or no report in 5 s:
                                     --> 5 Push Service (once, never retried)
                                - confirm the event to the bus after all recipients finish

RECONNECT
Client --WebSocket--> Gateway --> 6 set presence, then read the user's undelivered
                                   inbox rows, skip conversations the user has left,
                                   load bodies from Message Store, send in seq order
                                   per conversation; each client ack marks its row
                                   delivered
```

The steps below say where each piece of state lives and what each step does when it fails.

### Steps

1. **Save.** Trigger: the sender presses send.
   - The sender's client makes a msg_id and sends it with the text.
   - Message Service writes the message row and its outbox row in one Message Store transaction. The store assigns the seq in that same transaction.
   - Stored in: the Message Store (message, seq, outbox row).
   - If this sender already has a message with that msg_id, nothing new is written and the existing seq is returned. A retry never makes a second copy.
   - If the write fails, the sender gets an error. Nothing is stored and no one receives anything. The client retries with the same msg_id.

2. **Ack.** Trigger: step 1 commits.
   - The sender gets the msg_id and the seq through its gateway.
   - The ack does not wait for any recipient. Fan-out never runs on the sender's request path.
   - If the ack is lost, the client retries with the same msg_id and gets the same seq back.

3. **Publish.** Trigger: an outbox row is not yet marked published.
   - The Outbox Relay polls at a short interval for unpublished rows, in id order.
   - It publishes each row to the Event Bus, keyed by conversation id, with only the ids.
   - It then marks the row published. The row stays in the outbox until that mark, so a crash cannot lose the message.
   - Stored in: the outbox, until the mark.
   - If the relay or the bus is down, rows wait. Delivery is late, and nothing is lost.
   - Several relays may run at once, so a row can be published twice. The worker tolerates that. There is no database trigger and no lock. Publish order across relays is not guaranteed.

4. **Fan-out.** Trigger: a bus event.
   - The Fan-out Worker reads the message text once from the Message Store, using the event's conversation id, seq and msg_id.
   - It reads the conversation's members from the Message Store at this time, and removes the sender. Membership is read at fan-out time, not at save time.
   - It handles all recipients in parallel. For each recipient:
     - a. Inserts an Offline Inbox row (user, conversation, seq, msg_id) if none exists. An existing row is left alone. If the row is already delivered, it stops for this recipient.
     - b. Reads the Presence Registry. If the user is online, the entry names the gateway that holds the connection.
     - c. If online, the gateway sends the text to the client, and the client acks. The gateway marks the row delivered, then reports the ack to the worker. The worker waits up to 5 seconds for that report, using a timer, not polling. If the send fails at once, for example because the gateway is down or has no such connection, the worker does not wait. It treats the recipient as not delivered.
     - d. If the user was offline in b, the send failed, or no report came within 5 seconds, it goes to step 5. It does not wait for the push result.
   - It confirms the event to the bus only after every recipient has finished a to d, including the 5-second wait. It then takes the next event on that partition.
   - Stored in: the Offline Inbox (rows) and the Message Store (text and members). The Presence Registry is only read.
   - If a recipient hits an unexpected error in a, b or c, such as a database or registry error, that recipient stops and the event is not confirmed. The bus redelivers the event, and recipients already delivered are skipped. A failed text read is handled the same way. A push failure is never an error here.
   - Live messages of one conversation can arrive out of seq order, because two saves can commit in a different order than their seq. Clients sort by seq.

5. **Push.** Trigger: step 4d.
   - The Push Service sends one mobile push notification to the user's device.
   - The push carries only the conversation id and msg_id, not the text. The text stays in the Message Store.
   - Push is best effort. It is never retried, and a failed push changes nothing that is stored. The row stays undelivered.

6. **Reconnect.** Trigger: the client opens a WebSocket to a gateway.
   - The gateway sets the user's presence first, with its own id. This replaces any older entry.
   - It then reads the user's undelivered Offline Inbox rows. For each conversation, it checks that the user is still a member, and skips conversations the user has left.
   - It loads each message body from the Message Store and sends them in seq order per conversation. It does not need to know what the client already has.
   - Each client ack marks its row delivered.
   - Presence is set before this read, and each row is written in step 4a before step 4b checks presence. So each message is either in this read or sent live. A message can go out both ways, and the client drops the duplicate by msg_id.

### Presence

- The client sends a heartbeat every 10 seconds over its WebSocket.
- The gateway refreshes the user's Presence Registry entry, with the gateway's id and a 30-second expiry.
- If no heartbeat arrives for 30 seconds, the entry expires and the user counts as offline.

### What happens when things fail

| Failure | What happens |
| --- | --- |
| Save fails (step 1) | Sender gets an error. Nothing is stored and no one receives anything. The client retries with the same msg_id. |
| Ack lost after commit (step 2) | The client retries with the same msg_id. The store returns the existing seq. No second copy is made. |
| Gateway or sender crashes after commit | The outbox row remains, so fan-out still runs. |
| Relay or Event Bus down (step 3) | Outbox rows wait. Delivery is delayed and nothing is lost. |
| Relay crashes after publishing, before marking | The event is published again. Fan-out repeats safely: delivered recipients are skipped, and clients drop duplicates. |
| Text read from Message Store fails (step 4) | The event is not confirmed, so the bus redelivers it. Nothing is sent for it in the meantime. |
| Worker crashes during fan-out, or a recipient's step a, b or c fails | The event is not confirmed, so the bus redelivers it. Inserts find the existing rows. Undelivered recipients are tried again, so a push may be sent twice. Clients drop duplicates. |
| Gateway marks the row, but the report to the worker is lost or the worker crashes | On redelivery, step 4a finds the row delivered and stops for that recipient. No push and no resend. The client already has the message. |
| Mark write fails (step 4c) | No report is sent. The worker times out after 5 seconds and sends the push. The row stays undelivered until reconnect, which sends it again. |
| Presence says online, but the user has dropped | No ack within 5 seconds. The row stays undelivered and the push is sent. The message reaches the user at reconnect. |
| Presence names an old gateway after the user reconnected elsewhere | Reconnect replaced the presence entry, so this is only a stale read. The send to the old gateway fails at once, because it has no connection for the user. The worker treats the recipient as not delivered and sends the push. The reconnect read delivers the row. |
| Live send fails at once (gateway down, or no such connection) | The worker treats the recipient as not delivered and sends the push at once. It does not wait 5 seconds. |
| Client ack arrives after 5 seconds | The gateway marks the row delivered. The push already sent is not recalled. Any later fan-out repeat stops at step 4a, so no further push is sent. A second push is still possible only if the event is redelivered before that mark lands. Clients drop duplicates. |
| Push fails (step 5) | Nothing else changes. The row stays undelivered. The push is not retried. |
| Reconnect read is interrupted | Undelivered rows stay. The next reconnect sends them again. Clients drop duplicates. |
| Live send during the reconnect read | The message may go out both live and in the read. This is expected. Clients drop duplicates. |
| User has left a conversation | Its existing rows stay until they expire. The reconnect read skips them. |
| Member removed before fan-out | Gets nothing. |
| Member added after the save | No live message and no push. They see the message only in history. |
| Slow recipient | Later events on the same bus partition wait up to 5 seconds. |
| Two saves in one conversation commit in a different order than their seq | Live messages may arrive out of seq order. Clients sort by seq. Reconnect still sends in seq order. |
| Inbox row passes 30 days | The row expires, delivered or not. The message stays in the Message Store, if the store keeps it (see open questions). |

### Open questions

- Does the Message Store keep history for longer than 30 days? If it does not, a client that was offline for more than 30 days cannot recover that message.
- A connected client whose ack is late or missing keeps its row undelivered and gets the message only at its next reconnect. While its heartbeats continue, it may never reconnect, so 'eventually reach every recipient' may not hold for it. Should the gateway re-read undelivered rows for connected users?
- Does the Message Store enforce uniqueness on (sender, msg_id)? The duplicate-save rule in step 1 depends on it.
- Does the Message Store keep seq unique within a conversation when two saves run at the same time? Step 1 depends on the store assigning it.
- Where are each user's push device tokens kept, and who writes them? The brief does not say, and Push Service needs one to reach the device.
- Writing one inbox row per recipient means up to 199 writes per message. No cost or capacity target is set.
- The Event Bus must keep events for less than 30 days. Otherwise a redelivered old event could insert an inbox row again after the first one expired. No retention is set.
- Recipients are read at fan-out time, so a member added after the save gets no live message or push. Should the recipient list be fixed at save time instead?
- How long does the client wait for an ack before it retries a save, how many times does it retry, and when does it give up? The brief says it retries with the same msg_id but sets none of these.