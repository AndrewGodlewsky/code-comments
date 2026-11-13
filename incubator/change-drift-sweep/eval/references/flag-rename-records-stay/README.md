# reportctl

Command line for the reporting service.

## Usage

```sh
reportctl export orders.csv --after 2026-01-01 --output recent.csv
```

Leave out `--output` to write to stdout.
See [docs/cli.md](docs/cli.md) for every option, and [docs/incidents/](docs/incidents/) for past incidents.

Run the tests with `python -m unittest`.
