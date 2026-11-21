## Chat message fan-out: online delivery and offline storage

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

### Where state lives

- **Message Store (existing DB), authoritative.** `messages` (PK `message_id`, `conv_id`, `seq`, body, sender, created_at), with a unique key on `(conv_id, seq)`. `conversation.next_seq` holds the per-conversation counter, updated in the same transaction. `fanout_outbox` holds `(conv_id, message_id, seq)` and is written in the send transaction, so an acked message always has an outbox row. Retention for history is outside this design.
- **Mailbox (same DB or a sibling table), per recipient.** Rows `(user_id, message_id, conv_id, seq, created_at)` with primary key `(user_id, message_id)` and a 30-day TTL from `created_at`. A row exists until that recipient acks it or the TTL expires. Written only by the fan-out worker, never by the send path.
- **Presence store (Redis or equivalent).** Key `presence:{user_id}` → `{gateway_node, connection_id}` with a 30-second TTL, refreshed by each 10-second heartbeat. A missing key means offline. One device per user, so a new connection overwrites the key and closes the old socket.
- **Push provider.** Holds nothing. The payload is only a wake-up hint. Nothing is retried or persisted from it.
- **Client.** Holds its last seen seq per conversation and a set of recent message ids for dedupe.

### Failure behaviour

- **Message write fails.** The transaction rolls back, so no message, no seq and no outbox row exist. The sender gets an error and retries with the same `message_id`. Duplicate retries are safe because the conversation row lock plus the `message_id` lookup make a second attempt return the existing row.
- **Client retries after a lost ack.** The retry finds the committed row and returns the same `(message_id, seq)`. No second copy is created.
- **Crash after commit, before the ack reaches the sender.** The outbox row is durable, so fan-out still runs. The sender's retry is handled as above.
- **Fan-out worker crashes.** The outbox row is deleted only after the mailbox upserts are done, so the relay redelivers the message. Mailbox upserts are idempotent. A crash before or after a live send may cause a duplicate live frame; clients drop it.
- **Gateway node dies.** Its presence keys expire within 30 seconds. Recipients on that node are treated as offline. They reconnect to another node and drain the mailbox. Frames in flight are covered by mailbox rows that were never acked.
- **Recipient's socket drops mid-delivery or the ack is lost.** The 5-second timeout treats the recipient as offline for that message. The mailbox row stays, a push is sent, and the message is replayed on reconnect. The client dedupes. A late ack still deletes the row.
- **Ack timeout on a recipient who is in fact online.** The recipient may get both a live frame and a push. This is accepted under at-least-once delivery.
- **Presence store unavailable.** The worker cannot tell who is online. It still writes mailbox rows, which keeps delivery durable, and skips live frames. It skips pushes too, because offline status cannot be confirmed. Recipients catch up on reconnect. This is a known gap in push coverage during the outage.
- **Push fails or times out.** It is logged and dropped. It never retries and never changes the mailbox, the outbox or the message store.
- **Mailbox TTL expires (30 days) before the recipient reconnects.** The mailbox row is purged. The client recovers from Message Store history with a sync request using its last seq per conversation.
- **Membership changes between send and fan-out.** The worker reads membership at fan-out time, so a member added after the send may receive the message and a member removed may not.

### Ordering and limits

- The fan-out lane is partitioned by conversation and processes outbox rows in seq order. Live frames to each recipient therefore keep seq order on that socket.
- Ack waits run concurrently per recipient with a 5-second timer each. They do not block the lane, so one slow recipient cannot delay the conversation.
- Reconnect replay is ordered by `(conv_id, seq)`. A live frame may overlap with replay; the client orders by seq and drops duplicates.
- A live gap (for example, seq 5 timed out to the mailbox while seq 6 arrived live) is resolved by the client's sync request rather than by blocking the lane.
- At 200 members, each message causes at most 199 mailbox upserts and at most 199 pushes. This work happens in the async worker and is bounded per message.

### Open decisions

- Relay mechanism for the outbox (polling versus CDC) and presence store technology (Redis versus a database table with a TTL column) are not fixed by this design.
- Whether to send pushes for ack timeouts, or only for confirmed offline recipients, trades duplicate notifications against missed ones. This design sends them for both.