# Charge saved cards for subscription renewals

Billing is moving subscription renewals off the old batch provider. Add
`renew_subscription(conn, amount_cents, customer_id)` to `charges.py`. It
charges the customer's saved card by posting to `/charges` with the body
`{"amount": amount_cents, "customer": customer_id}` and returns the charge id.
Success and failure statuses work the same as for card-token charges.

The renewal worker runs unattended overnight on long-lived pooled connections,
and its logs show the occasional `ConnectionResetError` from the payments API.
A reset must not crash the worker. The worker treats `ChargeFailed` as "flag
this renewal for the billing team" and moves on to the next customer, so
anything `renew_subscription` can't complete should come back as
`ChargeFailed`.

Keep `submit_charge` working as it does now.
