I updated docs/limits.md to match the code. No code was changed.

What changed:
- Search: 50 results per page is now 100 (PAGE_SIZE = 100; the test asserts 100).
- Address lookups: the timeout is now 10 seconds, not 5 (GEOCODE_TIMEOUT_SECONDS = 10).
- Address lookups: the doc now states the portal's configured rate of 250 requests a minute. It also notes that lookup() does not enforce that rate, and that MIN_INTERVAL is computed but unused.
- Account export: the doc said deleted accounts are left out. The code writes every account, with the deleted flag in its row, so I corrected that description.
- Account export: app/schedule.py only computes the next 02:00 UTC start. The repository does not contain the job that triggers the export, and the doc now says so.

Conflicts for you to decide on (kept as stated, not resolved):
1. Privacy policy section 4 requires deleted accounts to be left out of the export, and I kept that requirement in the doc. The code does not do this, so the export currently contains deleted accounts.
2. The portal is configured to send 250 geocoding requests a minute, but Mapline's free tier allows 100 per API key. I kept the Mapline free-tier fact as written. Nothing in the code enforces a limit, so the portal can exceed the free tier if it runs on that plan.
