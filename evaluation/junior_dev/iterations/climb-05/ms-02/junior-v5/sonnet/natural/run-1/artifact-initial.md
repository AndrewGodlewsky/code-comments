# Plan: extract notifications into a Notification Service

## Design in brief

Callers keep calling `enqueue_notification(tx, ...)`. The monolith's `notifications` table is still where every notification is first recorded, in the caller's transaction. Only the sending moves.

**Monolith row states** (`status` column). `handed_off` is new. The other three exist today.

| status | meaning |
|---|---|
| `pending` | Recorded, not yet claimed by a sender. Either the old worker or the new dispatcher can take it, depending on the type's route flag. |
| `handed_off` | The broker confirmed storing the handoff message. The service now owns delivery and retries. |
| `sent` / `failed` | Terminal. For `handed_off` rows, the monolith learns this from an outcome event. |

**Route flags.** There is one flag per type, `notifications.route.<type>`, with the value `monolith` (default) or `service`. The flag decides which monolith component may claim a `pending` row. It is read through `flags.get`, so it takes effect on every instance within 10 s.

**Service row states** (service DB): `received` (pending), `sent`, `failed`. Each row also holds `attempts`, `next_attempt_at` and `lease_until`.

**Why nothing is lost or duplicated**

- **No loss.** A row stays `pending` in the monolith until the broker confirms the handoff. The service acks a handoff only after its own commit. Every `handed_off` row must produce an outcome event, or a reconciler republishes it.
- **No duplicates.** Every handoff is deduplicated on `id` in the service. Every MailRelay call carries `idempotency_key = id`, on both sides, so a duplicate send inside MailRelay's 24 h window is dropped.
- **Honest limit.** The key protects only within 24 h. The plan alerts on any in-flight notification older than 1 h, so a human acts long before the window closes.

**Roles of the pieces**

- **Dispatcher** (monolith). Reads `pending` rows for service-routed types and publishes them to the broker.
- **Outcome consumer** (monolith). Applies `sent`/`failed` events to the `notifications` table.
- **Service consumer, sender and outbox publisher** (service). They receive handoffs, send to MailRelay, and publish outcomes.

---

## Steps

### 1. Pass `idempotency_key` on the old worker

- **Starts when:** immediately. This is a one-line change in `_deliver`: `mailrelay.send(..., idempotency_key=row.id)`. Deploy it as an ordinary monolith release.
- **Data moves:** only the extra argument to MailRelay. No schema change.
- **State:** unchanged. The `notifications` table is still the only state.
- **Failures:**
  - *Instance crashes after MailRelay accepted part of a batch but before the commit.* The rows stay `pending` and are re-sent on the next poll, a few seconds later. MailRelay drops them because the key matches. This fixes the roughly 30 duplicate emails a week.
  - *MailRelay timeout or error.* Behaviour is unchanged. The retry reuses the same key, so a timeout that actually delivered the email is not delivered twice.
- **Done when:** one full release cycle has passed and support reports no new duplicates. This step is a prerequisite for every later step, because after it the service and the old worker share the same dedupe key.

### 2. Make the old worker route-aware (all flags `monolith`)

- **Starts when:** step 1 is live.
- **Data moves:** a schema migration adds the `handed_off` status value and a `handed_off_at` column. Create the flags `notifications.route.shipping_update`, `.order_confirmed` and `.password_reset`, each set to `monolith`.
- **State:** unchanged. The old worker's claim query gains `AND type = ANY(<types whose flag is 'monolith'>)`, with the flag read at the start of each batch.
- **Failures:**
  - *Flag read fails or returns nothing.* Default to `monolith`, so the old worker keeps behaving exactly as today.
  - *Mixed versions during a rolling deploy.* Every flag is `monolith`, so old and new workers behave identically.
- **Done when:** all instances run the route-aware worker. This must be true before any dispatcher exists. Otherwise an old-code instance could claim rows meant for the service.

### 3. Build and deploy the Notification Service, with no traffic

- **Starts when:** can run in parallel with steps 1 and 2. It must be live before step 4 is enabled.
- **Components and state:**
  - **Service DB**, separate from the monolith's. The `notifications` table has `id` (primary key), `type`, `user_id`, `email`, `payload`, `created_at`, `status`, `attempts`, `next_attempt_at`, `lease_until` and `paged`. An `outbox` table holds outcome events.
  - **Consumer** on the topic `notification.requested`.
  - **Sender** worker.
  - **Outbox publisher** for the topic `notification.outcome`.
  - **Templates**, moved here.
- **Consumer behaviour:**
  1. Insert the row with `INSERT ... ON CONFLICT (id) DO NOTHING`. The handoff carries `attempts` and `next_attempt_at`, so a row the old worker already tried keeps its retry budget.
  2. If the row already exists and is terminal, write the outcome event to the outbox again.
  3. Commit.
  4. Only then ack the broker message.
- **Sender behaviour:**
  1. Claim a due row with `UPDATE ... SET lease_until = now()+2min ... RETURNING`, and commit. No transaction stays open during the send.
  2. Render the template, then `send(..., idempotency_key=id)`.
  3. On success, set `sent` and write an outbox event in one commit.
  4. On `mailrelay.Error` (this includes a render failure, which counts as an attempt):
     - Increment `attempts`.
     - If `attempts < 5`, set `next_attempt_at = now() + [1,2,4,8][attempts-1]` minutes.
     - If `attempts >= 5`, set `failed` and `paged=false` in one commit with the outcome event. A separate pager step then calls `alerts.page_oncall` and sets `paged=true`.
- **Failures:**
  - *Service crashes after MailRelay accepted a send.* The lease expires and the row is re-sent. The key makes MailRelay drop it, and the sender records `sent`.
  - *Broker redelivers a handoff* (not acked within 30 s, or sent to a different consumer). The `ON CONFLICT` makes it a no-op.
  - *Poison message* (undecodable, or redelivered more than 10 times). It goes to a dead-letter queue and pages on-call, so it is not silently dropped.
  - *Broker down.* The consumer waits and retries. The outbox accumulates and drains later.
  - *MailRelay down.* The normal retry policy applies, ending in `failed` plus a page. The pager retries until `paged=true`, so a page is at-least-once.
  - *Service DB down.* The consumer cannot commit, so it does not ack and the broker redelivers.

### 4. Add the dispatcher, outcome consumer and reconciler to the monolith (inactive)

- **Starts when:** steps 2 and 3 are complete. All flags are still `monolith`, so the dispatcher finds nothing to do.
- **Dispatcher (every 1 s):**
  1. In a short transaction, run `SELECT ... WHERE status='pending' AND next_attempt_at <= now() AND type = ANY(<service-routed types>) ORDER BY created_at LIMIT 50 FOR UPDATE SKIP LOCKED`.
  2. Publish one message per row, carrying `id`, `type`, `user_id`, `email`, `payload`, `created_at`, `attempts` and `next_attempt_at`. Wait for the broker's storage confirmation.
  3. Set `status='handed_off', handed_off_at=now()` and commit.
  - Dispatcher polling is 1 s, faster than the old worker's 5 s, so the 60 s target for `password_reset` has margin.
- **Outcome consumer:** `UPDATE notifications SET status = :s WHERE id = :id AND status = 'handed_off'`. It acks after the commit. Updates only move forward, so redelivery is harmless.
- **Reconciler (every 5 min):** republish any `handed_off` row older than 30 min. That is twice the 15 min retry window. The service dedupes it, and for a terminal row it re-emits the outcome. Alert if a row is still `handed_off` after 1 h.
- **State:** the monolith table stays the record of origin. Delivery state for `handed_off` rows lives in the service.
- **Failures:**
  - *Dispatcher crashes after publishing but before the commit.* The row stays `pending` and is published again. The service dedupes on `id`. If the flag is flipped back to `monolith` in this window, the old worker may also send it. The shared key makes MailRelay drop the second send.
  - *Broker down.* Publishing fails and the transaction rolls back. Rows stay `pending` and nothing is lost. This does not consume the 5 delivery attempts, since the policy covers MailRelay sends. Alert if the oldest service-routed `pending` row is older than 2 min (30 s for `password_reset`). The remedy is to flip that type back to `monolith`, which rescues the backlog.
  - *Outcome event lost or delayed.* The reconciler repairs it.
  - *Monolith DB down.* Nothing here works, and enqueueing fails as it does today.

### 5. Verify before production traffic

- **Starts when:** steps 3 and 4 are deployed to staging, then to production with flags at `monolith`.
- **Data moves:** staging uses the MailRelay sandbox. A one-off monolith-side job writes sanitised sample payloads to a fixture file. The service never reads the monolith DB.
- **Checks:**
  1. **Rendering parity.** Render the fixtures with both the monolith and service templates. Output must be identical for all three types.
  2. **Chaos tests**, each asserting exactly one accepted email per notification id:
     - Kill the service consumer mid-handoff.
     - Kill the sender between MailRelay accept and commit.
     - Force broker redelivery of each message.
     - Take the broker down while the dispatcher runs.
     - Make MailRelay fail all 5 attempts and check the timing (1/2/4/8 min), the `failed` status and the page.
     - Kill the dispatcher after publish and before commit.
  3. **Rollback drill.** With load running, flip the type's flag back and forth, including mid-batch. Assert no loss and no duplicate.
  4. **Flag timing.** Measure flag-flip-to-effect and confirm it is under 60 s.
- **Failures:** any failed check blocks step 6.

### 6. Cut over `shipping_update` (40,000 a day, no latency requirement)

- **Starts when:** step 5 passes. Set `notifications.route.shipping_update = service`.
- **Data moves:**
  - New `shipping_update` rows are dispatched and handed off to the service.
  - Existing `pending` rows of this type, including ones the old worker had already tried, are picked up by the dispatcher with their `attempts` and `next_attempt_at`. The retry budget carries over, so the total is still 5.
  - Rows the old worker has locked mid-batch finish there. `SKIP LOCKED` means the dispatcher does not take them.
- **State:** delivery state for new rows lives in the service DB. Origin and final status are mirrored in the monolith.
- **Rollback:** set the flag back to `monolith`.
  - The dispatcher stops claiming the type, and the old worker claims new `pending` rows. This takes effect in about 10 s plus a poll.
  - Rows already `handed_off` are not touched by the old worker, because it only claims `pending`. They stay in the service until they finish and report back, so none are lost and none are re-sent.
  - The service keeps its consumer, sender and outbox running regardless of the flag.
- **Failures:** as in steps 3 and 4.
- **Watch for at least 3 days.** Move on only if all of these hold:
  - No duplicates reported.
  - No `handed_off` row older than 30 min.
  - The dead-letter queue is empty.
  - The failed-rate is no worse than before.
  - Service latency metrics are recorded: `created_at` to MailRelay accept, as p50/p99.

### 7. Cut over `order_confirmed` (12,000 a day)

- **Starts when:** `shipping_update` has run on the service for at least 3 days and its exit criteria hold. Set `notifications.route.order_confirmed = service`.
- **Data, state, failures and rollback:** same as step 6.
- **Extra:** this is the first type with a possible checkout correlation. Confirm checkout CPU and DB connection use have dropped as intended.
- **Watch for at least 3 days.** Record p99 enqueue-to-MailRelay latency (`created_at` to MailRelay accept). Report it for all sends, and separately for first-attempt successes.

### 8. Latency gate for `password_reset`

- **Starts when:** `order_confirmed` has run on the service for at least 3 days.
- **Gate:** p99 enqueue-to-MailRelay under 60 s on `order_confirmed`, measured over the whole 3-day window. Use `created_at` from the monolith and the accept time on the service host, with NTP-synced clocks.
- **If the gate is missed:**
  - Tune the dispatcher poll, the sender concurrency and the batch size.
  - Re-measure for a fresh window.
  - `password_reset` stays on the monolith until the gate is met. The other two types stay where they are.
- **Failures:** none during this step. It only reads metrics.

### 9. Cut over `password_reset` (1,500 a day, p99 under 60 s)

- **Starts when:** step 8 passes and `order_confirmed` has been on the service for at least 3 days. Set `notifications.route.password_reset = service`.
- **Data, state, failures and rollback:** same as step 6.
- **Extra:**
  - Page if the oldest service-routed `password_reset` `pending` row is older than 30 s.
  - Page if the p99 over the last hour exceeds 60 s.
  - The first response to either is a flag flip to `monolith`. It takes effect within a minute, and rows already handed off still finish in the service.
- **Watch for 7 days.**

### 10. Decommission the old worker

- **Starts when:** `password_reset` has run on the service for 7 days, all three flags are `service`, and the exit criteria hold.
- **Data moves:** none. This is a code removal.
- **Sequence:**
  1. Confirm no monolith-routed `pending` rows remain and no old-code instances are running.
  2. Release a monolith version that removes `run_worker`, `_deliver` and the monolith templates. This is safe because every flag is `service` and the old worker claims nothing.
  3. Keep `enqueue_notification`, the dispatcher, the outcome consumer and the reconciler. The dispatcher now routes every type.
  4. After a further clean release cycle, remove the route flags.
- **Consequence:** once the worker is gone, the flag-flip rollback no longer exists. Recovery would mean redeploying the old release. That is why the worker stays deployable for 7 days after the last cutover.
- **Failures:** same as step 4.

---

## Timeline

| day | event |
|---|---|
| 0 | `shipping_update` moves |
| 3 or later | `order_confirmed` moves |
| 6 or later | latency gate evaluated, then `password_reset` moves |
| 13 or later | old worker removed |

The earliest end-to-end finish is therefore about 13 days after the first cutover.
