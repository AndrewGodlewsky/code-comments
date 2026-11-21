## Review of pay-02 (junior, author haiku, natural)

Rounds: 2. Ended: teachback-correct.

### What changed
- Step 4 now ends the admin's request after commit; step 5 onward runs in a background worker, so the admin does not wait for retries and no lock is held during calls (Q1).
- Step 5 and 5b: the attempt count is written in its own committed transaction before each call (Q2).
- Step 9: a re-sent create that returns 2xx goes through step 6 and stores the provider id; webhooks that arrive before that get 503 (Q3, Q4).
- Step 5b and step 9: a 4xx on any retry or re-sent create goes to step 7 and marks the refund failed (Q5).
- Step 9: the status mapping for the retrieve API is stated as an assumption and added to open questions (Q6).
- Moved the order-status recompute and the email outbox insert into applyRefundTransition's definition, so they run on every path to succeeded; removed the separate step 11 (Q7).
- Removed the separate refund.final audit row; the terminal refund.status_changed row is the final record, and the final step lists the done checks (Q8).
- Restructured into terms, assumptions, the main flow, numbered steps with start, data, state and failure, a short cross-step failure section and open questions. Repeated rules (for example the 1-hour selection, 2-hour window and webhook 503) are each stated once.
- Added open questions: 429 handling was kept; added the retrieve status names, a 4xx on a repeated key, and a webhook that never matches a stored id.
- Kept every number and requirement from the brief and the first version, including 10-second timeout, 3 retries with backoff and jitter, 24-hour window, 15-minute job, 1-hour check, 2-hour re-send window, 20-hour and 24-hour alerts, the 403, 422, 400, 503 and 500 responses, and the audit rows.
- Step 5 now says how two callers are kept from both calling the provider: a conditional update on attempts, claimed before each attempt (Q9).
- Step 4's hand-off names the one-minute worker poll and that step 10 is the fallback (Q9).
- Step 10 (formerly 9) now says a re-send is one full up-to-4-attempt sequence per run, with the same claim and handling, and that attempts counts all calls (Q10).
- Step 10 now checks refunds with no provider id on every 15-minute run while they are under 2 hours old, so the first re-send is not delayed by an hour (Q12).
- Step 10's metadata lookup names the provider search or list call, and the plan says the provider's support for it is unknown (Q11).
- Step 7 (formerly 6) stores the provider id and audits it in one transaction with a row lock, and says how the webhook ordering works (Q14).
- Step 9 (formerly 8) says the webhook is assumed to carry the provider refund id (Q13).
- Terms: added 'conditional update'. applyRefundTransition now says it does not touch provider fields or last_status_check_at (Q13).
- Assumptions: added that the customer email, currency and payment reference come from existing data, and the outbox row stores only refund id and type (Q15).
- Step 11 (formerly 10): the worker reads the email, currency and payment reference when sending, and the outbox row holds only refund id and type (Q15).
- Removed the separate step 5b. Its retry handling is now step 6, and the steps are renumbered 1 to 12 so no step needs a half-number.
- Removed the cross-references to step codes such as 5b and step 9's old numbers; every step reference now uses the new numbers.
- Failure rules: added that every provider call has a 10-second timeout and claims its attempt first.
- Open questions: added the webhook body contents and the customer email, currency and reference data. Other open questions are unchanged.
- Rewrote the whole plan once for a newcomer, using all 15 junior questions and answers; kept every requirement, limit, number, rule and open question from the first version.
- Opening summary cut to three sentences: today's dashboard process, what the admin request does, and why the provider call and final result are handled in background jobs.
- Terms list expanded with plain definitions for claim, backoff with jitter, order status and the source values of applyRefundTransition; removed the separate order-status rule from step 11 so the rule is stated once, in the terms.
- Step 5 claim, step 6 retries, step 7 acceptance, step 9 webhook and step 10 reconciliation keep the Q&A corrections: attempts counted as calls made, the 1-hour check for refunds that have an id, the every-run check for refunds with no id created under 2 hours ago, and the locked, one-at-a-time acceptance write.
- Step 5 and step 6 now say the claim (a conditional update) is what persists attempts before each call, rather than repeating the same rule in two places.
- Step 9 'State' line added to say that applyRefundTransition writes the refund.status_changed audit row, and step 12 points to that row as the final record instead of repeating it.
- Step 12 no longer lists a separate final write, and the done-when criteria are kept as the closing check.
- Failure rules that cross steps moved into one short list after the steps, rather than repeated under each step; the step-level failure lines are kept where each step's own outcome applies.
- Step 7 webhook note clarified: a webhook arriving during the acceptance write waits on the same row lock, so the two never interleave.
- Nothing was dropped: the 403/422 codes, the 10-second timeout, the 3 retries, the 24-hour and 20-hour and 1-hour timings, the email unique constraint, the order status rule and all nine open questions are kept.

### Holes
- Q6: In step 9, the reconciliation job gets a status from the provider's retrieve API. What statuses can the provider return, and how do they map to our pending, succeeded and failed? What happens when it returns something still in progress? (author: The brief does not name the status values the retrieve API returns. Assumed: succeeded maps to succeeded, failed maps to failed, and any other value keeps the refund pending and updates last_status_check_at. Listed as an open question.)
- Q11: Step 9 says a refund without a provider id and 2+ hours old is looked up 'by our metadata'. What exactly is that lookup (which provider API call) and what do we do with the result? If the provider cannot do it, what does the refund look like to the admin in the meantime? (author: The brief does not say whether the provider can search or list refunds by our metadata refund id, so the exact API call is unknown. The plan uses the provider's search or list call with that metadata. If a refund is found, its id is stored as in step 7 and its status applied. If not found, it stays pending. Meanwhile the admin sees 'submitted, status being confirmed', because the refund is pending. If the provider cannot do this lookup, the open question on refunds with no id applies.)
