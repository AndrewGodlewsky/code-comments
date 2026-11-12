# payments-events

Takes payment events off the queue and turns each one into ledger postings.

- `events/queue.py`: takes events off the queue and posts the result.
- `events/dispatch.py`: hands each event to the handler for its kind.
- `events/handlers.py`: one function per event kind.
- `events/money.py`: pounds to pence.
- `config/routes.ini`: the event kinds this service accepts.
- `payouts/batch.py`: the weekly payout run.

Release notes are in CHANGELOG.md.
