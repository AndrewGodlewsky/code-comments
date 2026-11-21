# Chat message fan-out: online delivery and offline storage

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
 Send:      (1) client sends with client-generated msg id
            (2) Send API writes message + outbox row in one transaction; the store assigns seq
            (3) commit succeeds   (4) sender gets ack(msg_id, seq); on failure, an error and no outbox row
 Fan-out:   (5) relay publishes outbox rows to the queue, then marks them published
            (6) a worker takes the job   (7) per recipient: presence + backlog flag
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
| Message body, seq, unique key (conv, client_msg_id) | Message Store | Source of truth. Seq is assigned by the store at write time. |
| Outbox row (message committed, not yet published) | Message Store, same transaction as the message | This is what makes "acked implies eventually delivered" hold across crashes. It assumes the store can write two tables in one transaction. If it can't, use its change feed instead of a separate outbox table. |
| Fan-out jobs | Fan-out Queue | Durable and partitioned by conversation id. A job is acked only after every recipient is delivered or has an inbox entry. |
| Online status and node | Presence Store | One key per user, TTL 30 s, refreshed by each 10 s heartbeat. An expired key means the user is offline. |
| Backlog flag | Presence Store | Set when the user has any unconsumed inbox entry. It is a per-user simplification, so it also holds back live delivery in unrelated conversations until the drain finishes. |
| Missed messages | Offline Inbox | Key (user, conv, seq), value is the message id (the body is read from the Message Store). TTL 30 days. |
| Push | None | Fire and forget. Nothing is stored and nothing is retried. |
| Dedup | Client | Clients drop duplicates by message id. |

**Ordering.** Messages for one conversation go through one queue partition, and a worker handles them one at a time. Recipients within a message are handled in parallel, and each one waits at most 5 s for its ack. While a user's backlog flag is set, workers send that user nothing live and write inbox entries only. The inbox is therefore always a gap-free, ordered suffix of what the user missed. The drain sends it ordered by (conv, seq). A message that arrives during the drain goes to the inbox. The drain loops until the inbox is empty, and only then clears the flag. Cost: one dead recipient can hold a conversation's partition for up to 5 s per message. If that matters, the fix is to split delivery into per-recipient tasks.

**Failures**

- **Message write fails or times out:** The sender gets an error. No outbox row exists, so nothing is fanned out. The client retries with the same client message id. The unique key makes the retry either return the original (message id, seq) or perform the first write.
- **Write commits but the ack is lost:** The retry hits the unique key and returns the existing seq. No second copy is created, and the outbox row is not duplicated.
- **Crash after commit, before publish:** The outbox row is still unpublished, so the relay publishes it on restart. The relay is at-least-once, so the queue may see duplicates. Fan-out is idempotent, and clients dedup.
- **Worker crashes mid-fan-out:** The job is redelivered and reprocessed from the start. Recipients who already got the message may get it again, which clients dedup. Inbox writes are idempotent on (user, conv, seq). Send the push only when the inbox insert was new, which limits repeat pushes.
- **Recipient does not ack within 5 s, or the gateway node is dead or unreachable:** Treat the user as offline for this message. Write the inbox entry, set the flag, and push once. If the client did in fact receive it, the later duplicate is dropped by message id.
- **Presence goes stale (user is gone but the key hasn't expired):** The delivery attempt gets no ack within 5 s, so the offline path above applies. Worst case is a 5 s delay, not a loss.
- **Gateway node crash:** Clients reconnect to another node, which registers presence and drains the inbox. In-flight unacked messages were already headed for the inbox, or are redelivered via the job.
- **Failure during the drain:** Entries are deleted only after the client acks them. Anything unacked stays in the inbox and is resent on the next connect.
- **Push fails:** Ignored. It never touches the inbox or the Message Store and is not retried.
- **Inbox TTL expires after 30 days:** The entry disappears. The message is still in the Message Store, so the client gets it when it loads conversation history.
- **Queue or Presence Store outage:** Sends still commit and ack, because the outbox row is in the Message Store. Fan-out resumes and catches up when the dependency returns. If only the Presence Store is down, workers treat every recipient as offline, so they write inbox entries and push for everyone. That is safe but noisy.

**Assumptions**

- The Message Store supports a unique constraint on (conversation, client message id) and a transactional outbox or change feed.
- The ordering guarantee relies on there being one device per user.
