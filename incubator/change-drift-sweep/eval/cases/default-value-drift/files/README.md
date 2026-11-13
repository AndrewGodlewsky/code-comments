# Ledger exporter

Copies changed ledger rows into the warehouse every night.

- `exporter/client.py` pages through the ledger API.
- `exporter/sync.py` writes a night's rows in one transaction.

See [docs/api.md](docs/api.md) for how the API is called and
[docs/limits.md](docs/limits.md) for the limits the ledger team sets.

Run the tests with `python -m unittest`.
