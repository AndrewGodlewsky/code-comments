# Refunds plan

Today support staff refund customers in the card provider's dashboard, so our database never learns that a refund happened. Under this plan, an admin issues a full or partial refund from our internal admin page, and our server is the only part that calls the provider's refund API. The server saves a refund record before that call, so no request is lost. The provider's first reply only means "accepted", so the final result arrives later as a signed webhook, and an hourly reconciliation job checks pending refunds directly as a backup.

## Terms

- **Provider**: the card payment company. It holds the money and makes the actual refund. We call its API.
- **Captured amount**: the money the provider has taken for a payment, in cents.
- **Refundable amount**: the captured amount minus the sum of pending and succeeded refunds on that payment. Failed refunds are not subtracted.
- **Refund record**: our database row for one refund. It holds: id, payment id, amount in cents, reason, note, status, provider refund id, idempotency key, provider message, requested by, created time and an "email sent" flag. It starts as `pending`. Its status is `pending`, `succeeded` or `failed`.
- **Refund permission**: the admin permission that allows issuing refunds. Its name is not decided (see open questions).
- **Create-refund call**: our request asking the provider to make a refund.
- **Provider refund id**: the id the provider gives a refund when it accepts the create-refund call. We save it on the refund record.
- **Idempotency key**: a unique string sent with each create-refund call. If the provider gets the same key again within 24 hours, it returns the original refund and makes no second one. We make it a random UUID, store it on the refund record and reuse it for every retry.
- **4xx / 5xx**: HTTP status code families. A 4xx means the provider rejected the request. A 5xx means the provider failed to handle it.
- **Webhook**: a message the provider posts to our endpoint when a refund's result is known. It can arrive twice or out of order. Each one carries a **signature**, a value made with a secret key that we check to confirm the provider sent it.
- **Reconciliation job**: a task that runs every hour and checks pending refunds directly with the provider.
- **Payment row lock**: a lock on the payment's row in our database, held until the database transaction ends. Other writes on the same payment wait for it.
- **Order status**: what the order shows: normal, "Partially refunded" or "Refunded".
- **Audit entry**: a row that records who did what, to what, and when.

## Steps

- [ ] **1. Admin opens the payment page.**
  - Trigger: an admin opens a payment.
  - Data: reads the payment (charge id, captured amount, status) and its refunds with their statuses from our database. The page shows the refundable amount, each refund's status and the order status. The order status counts succeeded refunds only, so a pending refund does not change it.
  - If the refundable amount is 0, no refund form is shown. The page says that nothing is left to refund and that pending refunds count toward this.
  - The page does not update by itself. A newer status appears only after a reload.
  - On failure: if the payment cannot be loaded, the page shows an error. Nothing is written.

- [ ] **2. Admin submits the refund form.**
  - Trigger: the admin enters an amount in cents, picks a reason (duplicate, fraudulent, customer request or other), optionally adds a note and submits. The browser sends this to `POST /refunds` on our server. The browser never talks to the provider.
  - Permission: the caller must be an admin with refund permission. Otherwise the server returns 403.
  - Validation: the payment must be captured, the reason must be on the list, and the amount must be a positive whole number of cents. Otherwise the server returns an error.
  - Audit: every request that reaches this step gets an audit entry, including refused ones. The entry records the caller's id as who, the request, when, and the outcome: refused with the reason, or passed the checks. A 403 is audited the same way.
  - On failure: a 403 or validation error changes nothing except the audit entry.

- [ ] **3. Server checks the amount and saves the refund record.**
  - Trigger: step 2 passed.
  - In one database transaction, the server takes the payment row lock. A second request for the same payment waits until this one ends, then sees its result. This is what stops two admins from refunding past the captured amount at the same moment.
  - It computes the refundable amount. If the requested amount is more than that, it rejects the request, saves no refund and audits the rejection with its reason.
  - Otherwise it inserts a refund record with status `pending`, the amount, reason, note, payment id, the admin who asked, the time and a new idempotency key. The audit entry for the new refund is written in the same transaction. A successful request therefore makes two audit entries: the request from step 2, and this status entry. They record two different facts.
  - The transaction commits before step 4 starts.
  - Data: the refund table and the audit table.
  - On failure: if the transaction fails, nothing is saved, the admin sees an error and no provider call is made.

- [ ] **4. Server asks the provider to make the refund.**
  - Trigger: step 3 committed.
  - The server sends the create-refund call with the charge id, the amount and the idempotency key. The timeout is 10 seconds.
  - The call is made outside the payment row lock. A call that can wait about 40 seconds must not block other refunds on the same payment. The refundable-amount check still holds, because pending refunds already count from step 3.
  - Accepted: the server saves the provider refund id on the record in a short transaction under the payment row lock. The status stays `pending`. The plan does not rely on any status in the reply. The final result comes later, through step 6 or step 7.
  - 4xx: go to step 5.
  - Timeout or 5xx: retry up to 3 times with the same key. An accepted retry is handled as above. A 4xx on a retry goes to step 5.
  - If every attempt times out or gets a 5xx, the record stays `pending`. It is not marked failed, because the provider may already have made the refund. Step 7 resolves it.
  - If the id save fails after acceptance, the record stays `pending` with no id. Step 7 re-sends with the same key and gets the id back.
  - If the admin closes the tab, the server still finishes the call. If the server crashes mid-call, the record from step 3 stays `pending` with no id, and step 7 resolves it.
  - What the admin sees: the page waits until this step ends (accepted, rejected or retries used up). The server then reads the refund record from our database, not the provider's raw reply, and returns its status to the page. For a failure it also returns the provider message that step 9 saved. The browser makes no second call.
    - Accepted, or retries used up: shown as `pending`, with a note that the provider has not confirmed the refund and the status will update by itself. This is not an error, because the refund may already have been made.
    - Rejected: shown as `failed` with the provider's message, once step 9 has saved it. If step 9 has not saved it yet, the record is still `pending` and the page shows the pending note. Step 7 then re-sends, the rejection repeats and step 9 is tried again.
  - Later changes show only after the admin reloads the page (step 1).

- [ ] **5. Server marks a provider rejection (4xx) as failed.**
  - Trigger: a 4xx from the first call, from a retry in step 4, or from a re-send in step 7.
  - The server does not retry. It passes the status `failed` and the provider's message to step 9, which saves them.
  - The audit actor is the admin for a request, or "system" for a re-send from step 7.
  - A failed refund no longer counts toward the refundable amount.
  - A failed refund is never retried. A new form submission is a new request. It goes through steps 2 and 3 as a new refund, with a new record and a new key.

- [ ] **6. Provider sends a webhook: `refund.succeeded` or `refund.failed`.**
  - Trigger: the provider posts the event to our webhook endpoint.
  - The server checks the signature first. If the check fails, it rejects the request, changes nothing and logs the attempt.
  - It finds the refund record by the provider refund id saved in step 4. The new status comes from the event name: `refund.succeeded` gives `succeeded`, and `refund.failed` gives `failed`.
  - If no record has that id, the server returns an error so the provider sends the event again. This covers a webhook that arrives before step 4 saved the id.
  - A record moves only from `pending` to a final status. If it is already final, the event is a duplicate or a late event, and nothing changes. If a conflicting event arrives after a final status, the server keeps the first result and audits the conflict.
  - Otherwise, the server passes the new status to step 9. Once step 9 has committed, the server runs step 8 and returns 2xx, even if the email fails. The result is saved, and an error would only make the provider resend an event that changes nothing.
  - On failure: if step 9 fails, the endpoint returns an error, not a 2xx, so the provider sends the event again. A 2xx would tell the provider the event is done, and reconciliation is only a backup.
  - Data: the refund record.

- [ ] **7. Reconciliation job checks pending refunds.**
  - Trigger: runs every hour. The brief requires that no pending refund goes 24 hours without a direct check, so an hourly run leaves a wide margin.
  - Pending with a provider refund id: the job asks the provider for the refund's current status (pending, succeeded or failed). If it is still pending, nothing changes. If it is final, the job passes the status to step 9 directly, using the step 6 rules. It does not go through the webhook endpoint. If a webhook and the job reach the same record at once, both wait on the payment row lock in step 9. The first write sets the final status, and the second changes nothing.
    - A record with an id that stays pending for days is checked every hour with no limit. It gets no audit entry on each run, because its status does not change.
  - Pending with no provider refund id: the job checks the record's age, counted from creation.
    - Under 24 hours old: the job re-sends the create-refund call with the same key. If the first call got through, the provider returns the original refund. If not, it creates the refund. The job saves the id from the reply. It cannot tell a re-sent original from a new refund from the reply alone. It relies on the provider's key rule: within the window, the same key returns the original. If the reply shows a final status, the job applies it with the step 6 rules. A 4xx goes to step 5 with "system" as the actor.
    - 24 hours old or more: the job does not re-send, because the provider might then make a second refund. The record stays `pending`. The job writes one audit entry the first time it finds the record at 24 hours or older, not on every run. A person must then check the provider for this record.
    - Why 24 hours from creation: the provider's 24-hour key window starts when it first receives the key, which is after creation. So a re-send made within 24 hours of creation is still inside the window.
  - Any change to `succeeded` or `failed` goes to step 9.
  - Email pass: after the status checks in the same hourly run, the job finds `succeeded` refunds whose "email sent" flag is unset and runs step 8 for each. Running it as a separate pass also retries emails that failed earlier in the same run.
  - On failure: if the provider cannot be reached, the record stays `pending`. The next hourly run tries again.

- [ ] **8. Customer email on success.**
  - Trigger: step 9 has committed a change to `succeeded`. The email goes out only after the result is saved, so it is never sent for a result that was not saved. It runs in the same process, right after the commit, whether the trigger was a webhook or the job.
  - The server sends the customer one email, then sets the "email sent" flag on that refund record. The flag is on the refund, not the order. Once it is set, that refund is never emailed again.
  - Where the customer's email address comes from is not decided. Until it is, a missing address counts as a failed send.
  - On failure: if sending fails or no address is found, the flag stays unset and the failure is logged. The hourly email pass in step 7 retries it.

- [ ] **9. Order status update.**
  - Trigger: steps 5, 6 or 7 pass a new status, `succeeded` or `failed`. Those steps decide the status but never write it. This step is the only one that changes a refund's status after step 3 wrote it as `pending`. A new pending refund does not run this step, because a pending refund does not change the order status.
  - In one transaction, the server takes the payment row lock. This is the same lock steps 3 and 4 use, so this update and any new refund request on the same payment wait for each other. This matters because a failed refund frees up amount, and the lock stops a new request from reading the amount before that change is saved.
  - It saves the new refund status only if the record is still `pending`. If it is already final with the same status, nothing changes and nothing is audited. If it is already final with a different status, nothing changes and the conflict is audited.
  - It recalculates the order status from succeeded refunds only. No succeeded refunds gives the normal status. A succeeded total below the captured amount gives "Partially refunded". A succeeded total equal to the captured amount gives "Refunded". Pending and failed refunds are ignored. A failed refund usually leaves the order status unchanged, but the recalculation still runs.
  - The refund status, the order status and the audit entry are saved in the same transaction, so they cannot disagree. The audit actor is "system" for webhooks and the job, and the admin for a rejection at request time (step 5).
  - On failure: if the transaction fails, neither the refund status nor the order status changes, and the record stays `pending`. What happens next depends on the record:
    - A webhook is re-sent, which runs this step again (step 6).
    - A pending record with an id is checked by the job (step 7).
    - A pending record with no id, including a rejected call not yet saved as failed, is re-sent by the job with the same key while it is under 24 hours old. The provider should repeat the rejection, which reruns step 5 and then this step.

## Rules that apply to every step

- Only our server calls the provider. The browser never does.
- Writes to refund records (saving the provider id in step 4, step 3 and step 9) take the payment row lock. The provider call itself does not hold the lock.
- Every refund status change, including the first `pending`, gets an audit entry, written in the same transaction as the change. The entry records who (the admin's id, or "system"), what (the refund id and the old and new status, or the request) and when. Rejected requests are audited on their own.
- Amounts are whole numbers of cents.

## Open questions

- The brief does not name the refund permission or which admin roles hold it.
- The brief does not say whether anyone is alerted when a refund is still pending after 24 hours. For a refund with no provider id, the audit entry is the only record, so a person must find it.
- A refund with no provider id that is 24 hours old is not re-sent and not checked with the provider. This conflicts with the brief's direct-check rule. Who checks it, and how, is not decided.
- A refund with a provider id that stays pending for days is checked hourly but is not audited or escalated. Whether a person should be told is not decided.
- Several steps assume things the brief does not confirm. The create-refund reply may or may not carry a status. A status lookup exists and returns pending, succeeded or failed. Re-sending create-refund with the same key within 24 hours returns the original refund with its id and status. A re-sent rejected call gets the same 4xx. The job applies a final status only if the reply shows one.
- The brief does not say what fields a webhook carries. The plan assumes the event names the provider refund id, and that the event name gives the status.
- The brief does not say how long the provider keeps re-sending a webhook. If it stops, the reconciliation job still checks records with an id every hour and re-sends records with no id, so no record is left stuck.
- The brief does not say where the customer's email address comes from. The stored payment fields it names have no address. Until this is decided, a missing address counts as a failed send and is retried every hour with no limit.
- The brief does not say whether a double click on the form should be blocked. Two clicks create two refunds with two keys.
- Step 4 can keep the admin's page waiting about 40 seconds (four attempts of 10 seconds each). The brief sets no page time limit.
- If the server crashes after sending the email but before saving the flag, the customer may get the email twice. The plan does not prevent this.
- The brief does not say what a request with no signed-in user records in the audit entry. Step 2 covers only a signed-in caller.