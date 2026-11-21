# Plan: extract notifications

1. Add MailRelay idempotency keys to the existing worker.
2. Add a `route` column to `notifications` and per-type flags (`notify.route.<type>`).
3. Build the Notification Service: own database with a `deliveries` table, a broker consumer, a sender, and the templates.
4. Add an outbox relay in the monolith that publishes to `notifications.requested`.
5. Move `shipping_update` to the service.
6. Move `order_confirmed`.
7. Move `password_reset` once latency looks good.
8. Remove the old worker.

Notes:
- Retries: same policy as today.
- Dedupe on notification id.
- Rollback is a flag flip.
- Watch relay backlog, failed counts and latency during each move.
