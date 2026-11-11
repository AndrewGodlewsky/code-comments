`invoice_total` in `invoices/total.py` now sums quantity times unit price over the lines and rounds the sum once, half up to the cent, with `round_cents` from `money/rounding.py`. I checked that `round_cents` does round halves up (it uses `ROUND_HALF_UP`), and the existing tests pass.

- I rounded the total once, not each line. Your request only said "invoice totals", so say so if the tax office wants each line rounded before summing, because that can differ by a cent.
- I updated the `invoice_total` docstring to say the total is rounded half up and that the tax office requires it. I did not add a comment on the round-once choice, since nothing I read gives a reason for it.
