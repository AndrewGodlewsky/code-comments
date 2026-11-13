# reportctl options

## export

`reportctl export SOURCE [options]` writes the rows of SOURCE as CSV.
SOURCE is a CSV from the orders API, which filters the same way: `GET /orders.csv?since=2026-05-01` lists orders changed on or after 1 May.

| Option | Meaning |
| --- | --- |
| `--since DATE` | Only rows changed on or after DATE (YYYY-MM-DD). |
| `--output FILE` | Write to FILE instead of stdout. |

Without `--since`, every row is written.
`--since` shares its name and meaning with the API's filter, so a date copied from an API query selects the same rows.
