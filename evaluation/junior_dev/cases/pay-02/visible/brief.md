## Refunds from the admin page

Today, support staff refund customers by logging into the card provider's dashboard, so our database never learns that a refund happened. We want admins to issue full and partial refunds from our own internal admin page. Our system calls the provider's refund API and keeps its own record of every refund.

**Fixed requirements**

- Only payments that have been captured can be refunded, and only admins with refund permission can do it.
- Amounts are in cents. A payment can have several partial refunds. The total of pending and succeeded refunds on a payment must never exceed its captured amount. Failed refunds do not count toward that total. This must hold even when two admins refund the same payment at the same moment.
- Every refund needs a reason from a fixed list (duplicate, fraudulent, customer request, other) and can have a free-text note.
- Only our server talks to the provider. The browser never does.
- The provider's create-refund call takes an idempotency key. If a call is repeated with the same key within 24 hours, the provider returns the original refund instead of creating a new one.
- Give the call a 10-second timeout. On a timeout or a 5xx, retry up to 3 times with the same key. A 4xx means the provider has rejected the refund: mark it failed, don't retry, and show the admin the provider's message.
- The provider's immediate response only means "accepted". The final result comes later, sometimes days later, as a signed `refund.succeeded` or `refund.failed` webhook. Webhooks can be delivered more than once and out of order.
- No refund may stay pending for more than 24 hours without our system checking its status with the provider directly. Webhooks alone are not enough.
- Email the customer only after the refund has actually succeeded, and only once per refund.
- The order shows "Partially refunded" or "Refunded" based on succeeded refunds only.
- Write an audit entry (who, what, when) for every refund request and every status change.

**Existing system:** we already store payments with the provider's charge id, the captured amount and a status. There is no refund table yet.

**Format:** write the plan as a **Markdown checklist of steps, in the order they are done**. Start at the admin opening the payment and end when the final outcome is recorded. For each step, say what starts it, what data moves, where state is stored and what happens on failure.
