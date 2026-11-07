# Deduplicate the cent rounding in invoices.py

`invoice_total`, `credit_note_total` and `tax_amount` each repeat the same
`quantize(...)` call. Pull it into one helper, `round_cents(amount)`, that takes
a `Decimal` and returns it rounded to cents, and use it in all three functions.
No behaviour change: every total must come out exactly as before.
