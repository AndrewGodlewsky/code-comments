# outbox-relay (existing service, do not change)

Every 1 s the relay reads up to 200 `outbox` rows with
`published_at IS NULL`, oldest first. For each row it publishes one message
to the `domain-events` topic, then sets `published_at`.

If the relay crashes between publishing and updating the row, the row is
published again on the next poll. Consumers must tolerate duplicate
messages with the same `event_id`.

Message body (JSON):

    { "event_id": "...", "event_type": "invoice.paid",
      "account_id": "...", "occurred_at": "...", "payload": { ... } }

## Message queue facts (managed service)

- At-least-once delivery. No ordering guarantee, even within one topic.
- Consumers must ack each message. An unacked message becomes visible
  again after the visibility timeout (default 30 s, max 12 h).
- Delayed delivery is supported, but the maximum delay is 15 minutes.
- Maximum message size is 256 KB.
- A topic can have a dead-letter topic. Messages land there after N failed
  receives; it cannot be queried, filtered or partially replayed.
