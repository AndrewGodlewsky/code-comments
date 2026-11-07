# Ticket 412: duplicate credits after gateway incidents

**Reporter (payments on-call):** The payment gateway delivers webhooks
at-least-once. During incidents it redelivers the same event, sometimes up to
72 hours later, and each delivery currently credits the customer again.

Every event carries a unique `event_id`. Please deduplicate on that. Do not
deduplicate on account plus amount: customers legitimately make repeat payments
of the same amount (subscriptions, split bills), and those must all be applied.

**Comment (reviewer):** I first assumed these duplicates came from our own retry
loop, but checked: our service never retries webhook handling. The redelivery is
entirely on the gateway side, so the fix belongs in `apply`, not in a retry wrapper.
