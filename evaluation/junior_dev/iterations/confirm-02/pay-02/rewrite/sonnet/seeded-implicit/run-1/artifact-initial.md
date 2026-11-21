# Refunds plan

- [ ] Admin page: add refund form to the payment page (amount, reason, note)
- [ ] API endpoint: POST /refunds (permission check)
- [ ] Validate amount against what's left on the payment
- [ ] Create refund record
- [ ] Call provider create-refund (idempotency key, 10s timeout, retries)
- [ ] Handle provider errors
- [ ] Webhook endpoint for refund.succeeded / refund.failed (verify signature)
- [ ] Update refund status
- [ ] Update order status (Partially refunded / Refunded)
- [ ] Customer email
- [ ] Reconciliation job
- [ ] Audit logging
