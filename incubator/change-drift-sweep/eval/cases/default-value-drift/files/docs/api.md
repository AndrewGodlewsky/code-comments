# Ledger API usage

The exporter reads `GET /ledger/changes` with `since`, `page` and `per_page`.
Results come back 50 rows per page, oldest change first.
Pages are numbered from 1, and a page shorter than the rest marks the end of the results.

Each request times out after 30 seconds.
