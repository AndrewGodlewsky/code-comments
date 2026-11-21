# Chat message fan-out: online delivery and offline storage

## Summary

Today, clients see new messages only when they reload conversation history. This design adds real-time delivery. The sender's message is written to the Message Store together with an outbox row, in one transaction, and the sender is acked once that commits. A relay then publishes the outbox row to a durable queue. Workers read each job and push the message to every online recipient through their gateway node. Anyone offline, or who does not ack within 5 seconds, gets an inbox entry and one best-effort push notification, and receives the entry when they reconnect. The outbox is there so a crash right after the write cannot lose a message that was already acked.

## Terms

- **Gateway node**: one of several servers that hold clients' WebSocket connections. Each client connects to one. It sends a heartbeat every 10 seconds.
- **Message Store**: the existing conversation history database. It is the source of truth and assigns each message a per-conversation sequence number (seq).
- **client_msg_id**: an id the client generates for each message. The store enforces that (conversation, client_msg_id) is unique, so a retry never creates a second copy.
- **Outbox row**: a record, written in the same transaction as the message, that says "committed but not yet published to the queue".
- **Relay**: a process that publishes unpublished outbox rows to the queue, then marks them published. It retries until it succeeds.
- **Fan-out queue**: a durable log of one job per message, split into partitions by conversation id.
- **Fan-out worker**: a stateless process that takes a job and delivers the message to each recipient.
- **Presence Store**: a key-value store with one key per user (user to gateway node, TTL 30 s). Each heartbeat refreshes it. An expired key means the user is offline.
- **Backlog flag**: a per-user flag in the Presence Store. It is set while the user has inbox entries not yet consumed.
- **Offline Inbox**: per-user storage of what they missed, keyed (user, conv, seq). The value is the message id. The body is read from the Message Store. Entries expire after 30 days.
- **Drain**: sending a reconnected user's inbox entries to their client, in order.
- **At-least-once**: a message may arrive more than once. Clients drop duplicates by message id.

## Rules that apply throughout

- One device per user in this version. A conversation has at most 200 members. The sender is not a recipient of their own message.
- A user is offline once 30 s pass with no heartbeat.
- Fan-out never runs on the sender's request path. The sender's ack never waits for any recipient.
- Push is best effort. It is never retried, and a failed push never affects what is stored.
- Out of scope: typing indicators, read receipts, edits and deletes.

## Diagram

```
   SENDER                                                        RECIPIENT (online)
 +--------+  (1) send(client_msg_id, conv, body)                 +-----------+
 | Client |---------------------------+                          | Client B  |
 |   A    |<--(4) ack(msg_id, seq)----+                          +-----------+
 +--------+  or error (write failed)  |                            ^  |
      ^                                v                      (9) deliver | (10) client ack
      | WebSocket                +-------------+                    |  v    (within 5 s)
 +----------+                    | Send API    |              +-----------+
 | Gateway  |--- (1) ---------->| (stateless) |              | Gateway   |
 | node X   |                    +-------------+              | node Y    |
 +----------+                          |                      +-----------+
                         (2) ONE transaction:                   ^   |  ^
                         insert message (unique conv+client_msg_id)  |  | (12) drain on reconnect
                         + outbox row                          |   |  |      in seq order
                                       v                       |   |  |
                          +------------------------+    (8) RPC |   |  | (11) heartbeat every 10 s
                          |     MESSAGE STORE      |   deliver  |   |  |      register conn
                          |  messages (seq per conv)|    to node |   v  |
                          |  outbox (unpublished)  |            |  +----------------+
                          +------------------------+            |  | PRESENCE STORE |
                                  |                             |  | user -> node,  |
                         (3) commit => ack sender (4)           |  | TTL 30 s;      |
                                  |                             |  | backlog flag   |
                      (5) outbox relay publishes                |  +----------------+
                          (retries until published)             |        ^
                                  v                             |        | (7) lookup presence
                       +--------------------+  (6) consume      |        |     + backlog flag
                       |  FAN-OUT QUEUE     |------------->+----------------------+
                       |  durable log,      |  one job/msg | FAN-OUT WORKERS      |
                       |  partition = conv  |              | (stateless)          |
                       +--------------------+              | members <= 200,      |
                                                           | skip sender          |
                                                           +----------------------+
                                                             |                  |
                                  (13) no ack in 5 s / offline / backlog        |
                                       write inbox entry                        |
                                                             v                  v
                                              +----------------------+   (14) after the inbox write,
                                              |   OFFLINE INBOX      |   one best-effort push
                                              | key (user, conv, seq)|   (never retried)
                                              | value msg_id, TTL 30d|        v
                                              +----------------------+   +-----------+
                                                                         | Push svc  |
                                                                         +-----------+

 FLOW
 Send:      (1) client sends with its client-generated msg id
            (2) Send API writes message + outbox row in one transaction; the store assigns seq
            (3) commit succeeds   (4) sender gets ack(msg_id, seq); on failure, an error and no outbox row
 Fan-out:   (5) relay publishes outbox rows to the queue, then marks them published
            (6) a worker takes the job   (7) per recipient: look up presence + backlog flag
            (8) online and no backlog: RPC to the recipient's gateway   (9) gateway pushes over WebSocket
            (10) client acks; the job is done for that recipient
            (13) offline, backlog flagged, RPC failed, or no ack in 5 s:
                 write inbox entry, set backlog flag   (14) then send one push
 Reconnect: (11) client connects, gateway registers presence, sets backlog flag (draining)
            (12) gateway reads the inbox ordered by (conv, seq), sends each entry, deletes it on client ack,
                 repeats until the inbox is empty, then clears the flag with a version check
```

## Notes

**Where state lives**

| State | Location | Notes |
|---|---|---|
| Message body, seq, unique key (conv, client_msg_id) | Message Store | Source of truth. The store assigns seq at write time. |
| Outbox row | Message Store, same transaction as the message | Makes "acked implies eventually delivered" hold across crashes. Assumes the store can write two tables in one transaction. If it cannot, use its change feed instead of a separate outbox table. |
| Fan-out jobs | Fan-out Queue | Partitioned by conversation id. A job is acked only after every recipient is delivered or has an inbox entry. |
| Online status and node | Presence Store | One key per user, TTL 30 s, refreshed by each 10 s heartbeat. |
| Backlog flag | Presence Store | A per-user simplification: it also holds back live delivery in unrelated conversations until the drain finishes. The flag carries a version that each inbox write bumps, so a drain clears it only if no entry arrived since its last read. |
| Missed messages | Offline Inbox | Key (user, conv, seq), value message id, TTL 30 days. |
| Push | None | Fire and forget. Nothing stored, nothing retried. |
| Dedup | Client | By message id. |

**Ordering.** All messages of one conversation go through one queue partition, and a worker handles them one at a time. Recipients of one message are handled in parallel, and each gets at most 5 s to ack. While a user's backlog flag is set, workers send that user nothing live and only write inbox entries. So the inbox is always a gap-free, ordered suffix of what the user missed. The drain sends it ordered by (conv, seq). A message that arrives during the drain goes to the inbox, and the drain loops until the inbox is empty before clearing the flag. Cost: one dead recipient can hold a conversation's partition for up to 5 s per message. If that matters, split delivery into per-recipient tasks.

**Failures**

| Failure | What happens |
|---|---|
| Message write fails or times out | The sender gets an error. No outbox row exists, so nothing is fanned out. The client retries with the same client_msg_id. The unique key makes the retry either return the original (message id, seq) or perform the first write. |
| Write commits but the ack is lost | The retry hits the unique key and returns the existing seq. No second copy and no second outbox row. |
| Crash after commit, before publish | The outbox row is still unpublished, so the relay publishes it on restart. The relay is at-least-once, so the queue may see duplicates. Fan-out is idempotent and clients dedup. |
| Worker crashes mid-fan-out | The job is redelivered and reprocessed from the start. Recipients who already got the message may get it again, and clients dedup. Inbox writes are idempotent on (user, conv, seq). Push only when the inbox insert was new, which limits repeat pushes. |
| Recipient does not ack in 5 s, or their gateway node is dead or unreachable | Treat the user as offline for this message: write the inbox entry, set the flag, push once. If the client did receive it, the later duplicate is dropped by message id. |
| Presence is stale (user gone, key not yet expired) | The delivery gets no ack in 5 s, so the offline path above applies. Worst case is a 5 s delay, not a loss. |
| Gateway node crashes | Clients reconnect to another node, which registers presence and drains the inbox. In-flight unacked messages were already headed for the inbox or are redelivered via the job. |
| Failure during the drain | Entries are deleted only after the client acks them. Unacked entries stay and are resent on the next connect. |
| Push fails | Ignored. It never touches the inbox or the Message Store and is not retried. |
| Inbox entry expires after 30 days | The entry disappears. The message is still in the Message Store, so the client gets it when it loads conversation history. |
| Queue or Presence Store outage | Sends still commit and ack, because the outbox row is in the Message Store. Fan-out catches up when the dependency returns. If only the Presence Store is down, workers treat every recipient as offline and write inbox entries and push for everyone: safe but noisy. |

**Assumptions**

- The Message Store supports a unique constraint on (conversation, client_msg_id) and a transactional outbox or change feed.
- The ordering guarantee relies on one device per user.

## Open questions

- Whether the per-user backlog flag is acceptable, or the flag should be per conversation. Today it is per user for simplicity.
- Whether a dead recipient holding a partition for up to 5 s per message is acceptable. The fix, per-recipient tasks, is described under Ordering.
- Whether the Message Store can write the message and outbox in one transaction, or must use its change feed.