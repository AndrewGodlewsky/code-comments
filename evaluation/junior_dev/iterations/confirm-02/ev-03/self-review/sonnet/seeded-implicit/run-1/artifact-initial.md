## Message fan-out

```text
Sender -> Gateway -> Message Service -> Message Store (+ outbox)

Outbox Relay -> Event Bus -> Fan-out Worker

Fan-out Worker: Offline Inbox, Presence Registry, Gateway, Push Service

Reconnect: Gateway, Offline Inbox, Message Store
```

Notes:
- Sender gets an ack with the seq.
- Outbox for reliability.
- Bus partitioned by conversation.
- Presence has a TTL; heartbeats every 10 s.
- Inbox tracks undelivered messages, 30-day expiry.
- 5 s delivery timeout.
- Push is best effort.
- Sync on reconnect, ordered by seq.
- Retries idempotent on msg_id.
- At-least-once; clients dedupe.
