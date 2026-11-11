# reportctl options

## export

`reportctl export SOURCE [options]` writes the rows of SOURCE as CSV.
SOURCE is a CSV from the orders API, which filters the same way: `GET /orders.csv?since=2026-05-01` lists orders changed on or after 1 May.

| Option | Meaning |
| --- | --- |
| `--after DATE` | Only rows changed on or after DATE (YYYY-MM-DD). |
| `--output FILE` | Write to FILE instead of stdout. |

Without `--after`, every row is written.
`--after` has the same meaning as the API's `since` filter, so a date copied from an API query selects the same rows.
