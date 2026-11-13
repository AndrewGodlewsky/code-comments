## Extract notifications into a Notification Service

Notification sending runs inside the monolith today and competes with checkout for CPU and database connections. We are moving it into a separately deployed Notification Service. Start by reading `existing/notifications.py` (today's enqueue function and in-process worker) and `existing/notifications-overview.md` (the notification types, how MailRelay behaves, facts about the broker and flags, and known problems). Your plan must build on what they describe.

### What is fixed

- **Callers don't change.** Business code keeps calling `enqueue_notification(tx, ...)` inside its own transaction. The monolith's `notifications` table stays the first place a notification is recorded.
- **Separate data.** The service gets its own database. The service never reads or writes the monolith's database, and the monolith never touches the service's. The message broker is the only channel between them, and it is at-least-once.
- **Nothing lost.** Every notification whose enqueuing transaction committed must end up either accepted by MailRelay or marked failed with on-call paged.
- **Nothing duplicated.** A user must never get the same notification twice: not after a crash, not after broker redelivery, and not during cutover or rollback.
- **Idempotency key.** Every send passes the notification's id as MailRelay's `idempotency_key`. Do this on the old worker too, before any type moves.
- **Retries.** Keep today's policy exactly (5 attempts, backoff of 1/2/4/8 minutes, then mark failed and page on-call), whichever side does the sending.
- **Rendering.** Template rendering moves into the service.
- **Cutover.** Move one type at a time, in this order: `shipping_update`, `order_confirmed`, `password_reset`. Each type runs on the service for at least 3 days before the next one moves. `password_reset` moves only after the service has shown p99 enqueue-to-MailRelay latency under 60 s on `order_confirmed`.
- **Rollback.** Moving any type back to the monolith must be a flag flip that takes effect within a minute and neither loses nor re-sends notifications already in flight.
- **Decommission.** Keep the old worker deployable until `password_reset` has run on the service for 7 days, then remove it.

### What I want back

A numbered, step-by-step plan in Markdown, with the steps in the order we would actually ship them. For each step, say what starts it, what data moves, where the state lives, and what happens when something fails (a crash, the broker or MailRelay being down, a redelivered message).
