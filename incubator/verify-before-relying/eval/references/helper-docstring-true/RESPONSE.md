`invoice_total` now passes its total through `round_cents`, which rounds halves up to the
cent, so 0.125 becomes 0.13 and 4.005 becomes 4.01. The tests pass.
