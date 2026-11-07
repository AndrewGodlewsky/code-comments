# Support refunds in the ledger

Finance wants refunds reflected in account balances. Add `Ledger.refund(event)`.
A refund event has the same fields as a payment event (`event_id`, `account`,
`amount_cents`). It reduces the account balance by `amount_cents` and returns the
account's new balance.

Refund events reach us through the same webhook endpoint as payment events.
Keep the existing payment behaviour unchanged.
