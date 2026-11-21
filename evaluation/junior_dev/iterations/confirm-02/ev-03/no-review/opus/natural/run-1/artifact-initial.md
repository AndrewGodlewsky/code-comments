# Chat message fan-out: online delivery and offline storage

```
SEND  (the sender waits for steps 1-4 only)

+----------+  1 send(conv_id,         +-------------+  2 one transaction:     +----------------------------+
|  Sender  |    client_msg_id, body)  |  Gateway A  |    conv.seq += 1        |       Message Store        |
|  client  |------------------------->|  + send     |    INSERT message       |  conversations (seq)       |
|          |                          |    handler  |    INSERT outbox row    |  messages                  |
|          |                          |             |------------------------>|    UNIQUE(sender_id,       |
|          |<-------------------------|             |<------------------------|           client_msg_id)   |
+----------+  4 ack(msg_id, seq)      +-------------+  3 committed, or a      |  fanout_outbox             |
                or error                                duplicate key: return |  shard_leases              |
                                                        stored msg_id + seq   +----------------------------+
                                                                                 |
FAN-OUT  (asynchronous; none of this is on the sender's path)                    | 5 claim pending rows,
                                                                                 |   one conversation at a
                                                                                 v   time, in seq order
+--------------+  6 members minus sender  +---------------------------------------------+
|  Membership  |------------------------->|               Fan-out Worker                |
+--------------+                          |  10 mark outbox row done once 7-9 issued    |
                                          +---------------------------------------------+
                                             |                |              |        |
                    7 insert-if-absent an    |  8 THEN look   |  9a online:  |        | 9b offline, or
                      entry for EVERY        |    up presence |   deliver    |        |    deliver failed:
                      recipient; wait for    v                v   RPC        |        v    push, at most once
                      the commit +------------------+  +------------------+  |   +--------------+
                             |  Offline Inbox   |  | Presence Registry|      |   | Push Service |--> phone
                             |  user_id ->      |  | user_id ->       |      |   +--------------+
                             |  (conv_id, seq)  |  |  (gateway,       |      |          ^
                             |   msg_id,        |  |   conn_id)       |      |          | 13 no ack in 5 s:
                             |   push_attempted,|  |  TTL 30 s        |      |          |    push, close socket
                             |   delivered      |  +------------------+      v          |
                             +------------------+                    +-----------------------+
                                      ^                              |       Gateway B       |
                                      |  12 client acked: mark       |  5 s ack timers       |
                                      |     entry delivered          |  (in memory)          |
                                      +------------------------------|                       |
                                                                     +-----------------------+
                                                                        | 11 message   ^ 12 ack(msg_id)
                                                                        v              |
                                                                     +-----------------------+
                                                                     |  Recipient (online)   |
                                                                     +-----------------------+

RECONNECT  (any gateway; R2 must finish before R3 starts)

+-------------+  R1 connect            +-------------+  R2 set user -> (C, conn_id), TTL 30 s
|  Recipient  |----------------------->|  Gateway C  |------------------------------> Presence Registry
|  (was       |                        |             |  R3 list undelivered entries, by (conv_id, seq)
|   offline)  |                        |             |------------------------------> Offline Inbox
|             |                        |             |  R4 fetch bodies by (conv_id, seq)
|             |                        |             |------------------------------> Message Store
|             |<-----------------------|             |
|             |  R5 messages, each     |             |
|             |     conversation in    |             |  R7 mark each acked entry delivered
|             |     seq order          |             |------------------------------> Offline Inbox
|             |----------------------->|             |
+-------------+  R6 ack(msg_id)        +-------------+
                 heartbeat every 10 s ----> refreshes the presence TTL; if the
                                            entry had vanished, run R3-R7 again
```

## Key decisions

- **Outbox in the send transaction.** The message row and its `fanout_outbox` row commit together, so an acknowledged message always has fan-out work recorded. Workers poll the outbox, with a short interval (or a nudge after commit) to keep latency low.
- **Inbox first.** The worker writes an inbox entry for every recipient before it tries live delivery. The inbox is the only record of "not yet received". An entry stops being pending only on a client ack, or when its 30-day TTL expires. Live delivery is just the fast path. The cost is up to 199 inbox writes per message.
- **No reconnect race.** Step 7 commits before step 8 reads presence, and R2 writes presence before R3 reads the inbox. If the worker's presence read comes after R2, it sees the new connection and delivers live. If it comes before R2, the entry committed before R2 and therefore before R3, so the drain finds it.
- **Push at most once.** Before calling the Push Service, the sender of the push (the worker in 9b, Gateway B in 13) flips `push_attempted` from false to true with a conditional update. It sends only if its own update flipped the flag. The flag is set before the call, so the outcome of the push never changes stored state.
- **Acked entries become tombstones.** On ack, an entry is marked `delivered`, not deleted, and kept for 24 h. If a worker redoes a fan-out, insert-if-absent then finds the tombstone. The worker skips live delivery and push for that recipient instead of bringing the entry back.
- **Ordering.** Each conversation's outbox rows go to one worker shard and are processed in seq order, so live messages normally arrive in order. During a drain, Gateway C holds back live messages for that connection. It sends them after the drain, skipping msg_ids it has already sent. The client always places messages by seq.

## Where state lives

| State | Lives in | Lifetime |
|---|---|---|
| Message body, msg_id, seq, (sender_id, client_msg_id) | Message Store `messages` | Durable, permanent history |
| Per-conversation seq counter | Message Store `conversations.seq` | Durable; incremented in the send transaction |
| Pending fan-out (msg_id, conv_id, seq, status) | Message Store `fanout_outbox` | Durable; written with the message, marked done at step 10 |
| Shard ownership (shard, worker, expires_at) | Message Store `shard_leases` | 15 s lease, renewed by the owning worker |
| What each user has not received | Offline Inbox, keyed by user_id, ordered by (conv_id, seq) | Durable; undelivered entries expire 30 days after commit, tombstones 24 h after ack |
| Who is online and where | Presence Registry: user_id -> (gateway, conn_id) | Soft state, 30 s TTL refreshed by heartbeats; can be lost |
| Open sockets, 5 s ack timers, drain hold-back buffer | Gateway memory | Lost on gateway crash; correctness does not depend on it |
| Unacked sends (client_msg_id, body) | Sender client | Kept until the ack arrives, for retries |
| Seen msg_ids, local history | Recipient client | Used to drop duplicates and to place messages by seq |
| Push attempts | Only the `push_attempted` flag | The Push Service holds nothing for us |

## Failures

| Failure | What happens |
|---|---|
| Message Store write fails | The transaction rolls back, so there is no message and no outbox row. The sender gets an error and nobody receives anything. The client retries with the same client_msg_id. |
| Write committed but the reply was lost (timeout, Gateway A crash) | The outbox row exists, so fan-out goes ahead. The client's retry hits the unique key and gets back the original msg_id and seq. No second copy is created. |
| Two retries race | The unique key lets one insert win. The other reads the winning row and returns the same ack. |
| Fan-out worker crashes during steps 5-10 | The lease expires after 15 s. Another worker claims the shard and redoes any rows not marked done. Inserts are insert-if-absent, tombstones block acked entries, the flag keeps push at most once, and clients drop repeated live messages by msg_id. |
| Offline Inbox or Membership unavailable | The worker retries with backoff and the row stays pending. Later messages in that conversation wait behind it to keep order. The sender is unaffected. |
| Presence Registry unavailable or wiped | The worker treats recipients as offline. Their entries are already stored, so it sends push. Gateways re-register on the next heartbeat (within 10 s). A missing entry triggers a drain, so connected clients catch up without reconnecting. |
| Deliver RPC fails, Gateway B is down, or conn_id is not open there | Treated as offline (9b): push is sent and the entry stays. If B died, the client's socket died with it, and the client reconnects and drains. |
| No client ack within 5 s | Gateway B sends push (via the flag) and closes the socket. It removes the presence entry only if that entry still names this conn_id. The entry stays undelivered. A live client reconnects at once and drains it. |
| Client got the message but its ack was lost | Same as the 5 s timeout. The message is resent on reconnect and the client drops it by msg_id. |
| Gateway B crashes with timers pending | Those entries stay undelivered. Push for them is skipped, which is allowed because push is best effort. The client reconnects elsewhere and drains. |
| Client vanishes without closing the socket | Presence expires 30 s after the last heartbeat. Until then, deliveries hit the 5 s timeout path. After that, the worker goes straight to 9b. |
| Push fails | It is logged and never retried. Stored state is unchanged. |
| Disconnect in the middle of a drain | Unacked entries stay undelivered. The next connect drains again from the lowest pending seq in each conversation, so order holds. |
| Message Store unavailable at R4 | Gateway C retries. If it still fails, it closes the connection with a retry-after. Entries are untouched. |
| Recipient away longer than 30 days | Expired entries are no longer streamed on reconnect. The messages are still in the history and show up on a history reload. |

## Assumptions

- The Message Store supports multi-row transactions. That lets the outbox and lease tables live beside `messages`. It also keeps history for at least 30 days.
- Sends go over the client's WebSocket through its gateway.
- Recipients are the conversation members at fan-out time, minus the sender.
