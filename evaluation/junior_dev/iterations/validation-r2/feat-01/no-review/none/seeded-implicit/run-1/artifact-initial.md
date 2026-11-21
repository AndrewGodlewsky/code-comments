# CSV export plan

1. Add a `report_exports` table.
2. Add `POST /api/reports/{report_id}/exports` with the usual permission check.
3. Small reports: stream the CSV back in the response.
4. Large reports: create an export record and enqueue a `report_export` job.
5. Job: read rows from the replica in batches, write the CSV to the `exports` bucket with a multipart upload, then email a signed link with `send_email` and mark the export done.
6. Page: show the export status (queued / running / done / failed) and poll for updates.
7. Prevent duplicate exports.
8. Errors: rely on the job queue's retries, abort the upload on error, and send a failure email at the end.
9. Cleanup is handled by the bucket lifecycle rule.
