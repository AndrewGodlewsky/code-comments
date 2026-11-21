## Review of ms-01 (rewrite-v7, author sonnet, natural)

Rounds: 0. Ended: simplify-only.

### What changed
- Rewrote the document into the required order: summary, terms, diagram, step notes, storage, rules, open questions.
- Cut the 'How to read this' bullets about outbox and inbox; they now live once in the terms. Added definitions for service, event, hold, claim, provider, idempotency key and webhook.
- Replaced the opening with a three-sentence summary of the main flow and why stock is reserved before payment.
- Merged failure handling into each step's notes instead of a separate telling; removed repeated statements about the cart, idempotency and the provider from the rules section.
- Merged the 'Assumptions to confirm' list into 'Open questions' and added the 5b re-take choice and the no-fifth-service point as items to confirm.
- Moved the cart-empties-by-version detail into step 6a, and the mailer note into the rules.
- Kept the Mermaid diagram unchanged, and kept every number, status name and requirement from the first version.
- Dropped the 'No service reads another's tables ... steps 1 and 2' wording and the cross-references to step numbers, now stated once in the terms.

### Holes
- None.
