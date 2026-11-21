# Notifications today

Code: `app/notifications.py` (runs inside the monolith). Owner: Platform team.

## Types

| type            | enqueued when                       | per day | requirement                         |
|-----------------|-------------------------------------|--------:|-------------------------------------|
| shipping_update | carrier webhook updates a shipment  |  40,000 | none                                |
| order_confirmed | checkout commits an order           |  12,000 | none                                |
| password_reset  | a user asks to reset their password |   1,500 | p99 enqueue-to-MailRelay under 60 s |

All three are email only, sent through MailRelay.

## MailRelay

- `send()` takes an optional `idempotency_key`. If MailRelay has already
  accepted a send with the same key in the last 24 hours, it drops the new
  one and returns success.
- We do not pass a key today.

## Known problems

- The worker commits once per batch. If an instance dies after MailRelay has
  accepted some of a batch but before the commit, those rows stay `pending`
  and are sent again. Support sees about 30 duplicate emails a week.
- Sending competes with checkout for monolith CPU and DB connections.

## Platform facts

- Message broker (already used by billing and search): at-least-once. A
  message that is not acknowledged within 30 s is redelivered, possibly to a
  different consumer. Publishers get a confirmation once a message is stored.
- Runtime flags: `flags.get(name)` in the monolith. A change reaches every
  monolith instance within 10 s.
