I updated docs/limits.md to match the code. No code was changed.

Changes:
- Search: 50 results per page becomes 100 (`PAGE_SIZE = 100` in app/config.py, and the test asserts 100).
- Address lookups: the timeout changes from 5 to 10 seconds (`GEOCODE_TIMEOUT_SECONDS = 10`). I added that the portal paces lookups to 250 a minute (`GEOCODE_REQUESTS_PER_MINUTE = 250`).
- Account export: the nightly 02:00 UTC time was already correct (`EXPORT_HOUR_UTC = 2`), so it is unchanged.

Conflicts that need your decision (code not changed):
1. Rate limit: the portal paces lookups to 250 a minute, but Mapline's free tier allows 100 requests a minute per API key. If the portal runs on the free tier, it will exceed the quota. I kept the Mapline free-tier statement as written, since it is an outside fact, and left the conflict visible in the doc.
2. Deleted accounts: the privacy policy (section 4) requires deleted accounts to be left out of the export. `export_accounts` in app/export.py writes every account, including deleted ones, with a `deleted` column. The doc now says what the code does and keeps the policy requirement as written. Someone needs to either filter deleted accounts in the export or confirm that the policy requirement is met another way.

Not settled by the evidence: nothing in the repo states why the export keeps deleted accounts, so I did not invent a reason.
