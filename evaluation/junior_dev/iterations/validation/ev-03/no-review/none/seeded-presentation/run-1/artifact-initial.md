## fanout design (notes)

So the basic idea is that the msgs table is the source of truth and everything else hangs off the outbox. When a send comes in over the socket the edge node forwards it to MsgSvc, which does one txn that inserts the message (msg_id is unique, seq is the next one for the conversation) plus an obx row, and only after that commits does the sender get its ack {msg_id, seq} back through the GW. If the txn fails it's an error to the sender, and since there's no obx row nothing gets published to anybody. A resend with the same client-generated msg_id just gets the stored msg_id/seq back from the history DB with no new row, which is also why it's fine if MsgSvc dies after commit but before acking: the obx row is committed so the fanout still happens and the client's retry gets the original ack.

```text
 [clients]<=ws=>[GW]-a->[MsgSvc]-b->[DB]-c->[relay]-d->[bus]
                 ^|                  ^                   |
                 ||                  |                   e
                 ||                  g                   v
                 |+-----k-----+      +--------------[dispatcher]
                 |            |                      |  |  |   |
                 +------i-----|----------------------+  |  |   |
                              v                         f  h   j
                           [inbox]<---------------------+  |   |
                                                           v   v
                                                         [PR] [push]
```

a fwd | b txn: msg + obx row | c obx rows | d publish message.created {msg_id, conv_id, seq, sender_id} | e consume | f put pending (user_id, conv_id, seq, msg_id) | g read members | h which node? | i to node's delivery queue | j push if no PR key | k delete on ack, read on reconnect
not drawn: ack/err back to sender, GW refreshing PR on heartbeat, GW -> push on timeout, GW reading bodies from DB on reconnect

- push svc failures are logged and that's it, no retry, the mailbox row is untouched.
- The relay / obx poller deletes a row only after the bus confirms the publish, so if it crashes between publish and delete, or the bus is down, the row just gets published later (maybe twice), and sender acks don't care either way.
- Reconnect (any edge node): R1 set presence user_id -> this node with 30 s TTL, R2 pull the user's entries out of the pending table, R3 bodies by msg_id from the DB, R4 send per conversation in ascending seq, R5 delete each entry as the client acks it. Anything live that lands during R2-R4 the client slots in by seq, and dup msg_ids get dropped.
- The dispatcher reads members (g), drops the sender, and for every recipient writes the undelivered-list entry (f) (pointers only, no bodies) before trying anything live. Then it asks the online map (h): no key = offline = push (j), key = node G = send to G's delivery queue (i). It acks the bus event only once every recipient is handled (entry written + handed to G or push requested; it doesn't sit waiting on the 5 s client ack), and the bus keeps redelivering until it's acked. So a crash halfway means another FO instance redoes the whole member list, which is fine since the inbox put is idempotent on (user_id, msg_id) and clients drop dup msg_ids.
- bus is keyed on conv_id: one conversation = one partition = events come off in publish order, which isn't strictly seq order since a relay republish can bring an old seq back after a newer one, so clients order by seq.
- online map / presence cache (in-memory KV): user_id -> gateway node, TTL 30 s. Every heartbeat (clients send one every 10 s) resets it, a clean disconnect deletes the key, otherwise 30 s of silence and the key expires and they count as offline.
- On the socket server side (G): write to the socket, start 5 s timer; client ack inside 5 s -> delete mailbox entry; no ack, or no socket for that user -> ask push svc and leave the entry. Sockets and timers are only in G's memory, so if G dies mid-delivery no push goes out, but the mailbox row is still there and the client gets it after reconnecting somewhere else.
- mailbox entries expire after 30 days (the message stays in history).
