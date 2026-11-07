# Make ledger events safe to apply twice

Customers are being double-credited. Make `Ledger.apply` safe to call more than
once for the same payment event, as described in `docs/ticket-412.md`. Keep the
return value: the account's balance after the call.
