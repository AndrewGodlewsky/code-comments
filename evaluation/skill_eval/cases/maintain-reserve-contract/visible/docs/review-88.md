# Review notes: PR 88 (order service)

**Sam:** Both the checkout flow and the admin re-order screen call
`reserve(...)` and ignore the return value. When stock runs out they carry on
and we ship orders we cannot fill. Rather than patching every caller, make
`reserve` raise `InsufficientStock` on a shortage so a caller that forgets to
handle it fails loudly instead of silently overselling.

**Noor:** Agreed. While you're changing the contract, have it return the
units left for that SKU on success. The low-stock alert then doesn't need a
second lookup. Keep the guarantee that a failed reservation doesn't touch
`stock`.
