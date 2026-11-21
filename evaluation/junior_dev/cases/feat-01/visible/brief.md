# CSV export for the reports page

Users keep asking for a **Download CSV** button on the reports page. Please plan it. Three files describe the parts that already exist. Read them first:

- `existing/reports_page.md`: how the page and its API load rows today
- `existing/jobs.py`: our background job queue
- `existing/storage.py`: object storage helpers and the `exports` bucket

## What is fixed

- **Contents.** The CSV holds what the user is looking at when they click: the filters and column order from the page URL, plus a header row. Export uses the same `report.view` permission check as the page. Like the page, it reads report rows only from the read replica.
- **Two paths, by size.** Decide by `reports.row_count`. At 10,000 rows or fewer, the response to the click *is* the CSV: no job runs and nothing is stored. Above 10,000, the click returns straight away and a background job builds the file.
- **Large exports.** The job writes the file to the `exports` bucket and emails the user a download link that works for 24 hours. Send it with the existing `send_email(user_id, template, params)`. Leave deleting old files to the bucket's existing lifecycle rule. Do not build a cleanup job.
- **Status on the page.** While a large export is queued or running, and when the user comes back to the report later, the page shows the export's state: queued, running, done or failed.
- **One at a time.** A user can have only one large export of a given report queued or running. Clicking again returns that export instead of starting a second one.
- **Size limits.** A worker has 512 MB of memory and our largest report is about 2 million rows. The job must never hold a whole report in memory, and it has to finish within the queue's attempt timeout.
- **Failure.** Use the queue's normal retries. A half-written file must never be downloadable. When the last attempt fails, email the user that the export failed and show it as failed on the page.

Out of scope: scheduled exports, formats other than CSV, and changes to the table on the page.

## What I want back

A **numbered, step-by-step plan in Markdown**. For each step, say what starts it, what data moves, where any state is kept, and what happens when it fails. Assume the reader has never seen our codebase.
