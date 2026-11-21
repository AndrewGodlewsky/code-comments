# Reports page: current behaviour

The page lives at `/reports/{report_id}`. It renders one report as a table
with infinite scroll.

## Loading rows

The page calls:

    GET /api/reports/{report_id}/rows?filters=...&cols=...&after={row_id}&limit=500

- The API first checks that the caller has the `report.view` permission on
  the report's workspace, and returns 403 otherwise.
- Rows come from the `report_rows` table on the **read replica**. Report data
  must never be read from the primary database.
- Every row has a `row_id` that is unique and increasing within its report.
  The API pages by `row_id` (keyset: `row_id > after ORDER BY row_id`), never
  by OFFSET, so every page is equally fast.
- API servers kill any request that runs longer than 60 seconds.

## View state

Filters and column order live only in the page URL, for example
`/reports/42?status=open&region=EU&cols=date,customer,amount`. The server
stores nothing about what a user is currently looking at.

## Report size

`reports.row_count` holds the total (unfiltered) number of rows. It is
rewritten when the report data is rebuilt each night. The largest report
today has about 2 million rows, roughly 900 MB as CSV.
