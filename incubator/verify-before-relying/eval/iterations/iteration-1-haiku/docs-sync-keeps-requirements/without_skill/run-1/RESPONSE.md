I updated docs/limits.md to match the code. No code was changed.

Changes made:
- Search: 50 results per page becomes 100 (`PAGE_SIZE = 100` in app/config.py).
- Address lookups: the rate is now the portal's configured 250 lookups a minute (`GEOCODE_REQUESTS_PER_MINUTE`), and the timeout is 10 seconds (`GEOCODE_TIMEOUT_SECONDS`), not 5.
- Account export: the start time of 02:00 UTC still matches `EXPORT_HOUR_UTC`. I reworded "runs nightly" to "starts at 02:00 UTC each day", since the code only sets the start hour. I also listed the export's columns.

Items that need your decision:
1. Privacy policy gap. The old doc said deleted accounts are left out of the export "as section 4 of the privacy policy requires". `export_accounts` in app/export.py writes every account it receives, including those with `deleted` set, and does not filter them. Any exclusion would have to happen in the caller, which is not in this repository. I wrote the doc to describe the code as it is. Someone should check whether the filter exists upstream, or add it, before the privacy claim is restored.
2. Mapline free tier. The old doc said "Mapline's free tier allows 100 requests a minute per API key". Nothing in the code shows that, and I can't verify it from here, so I removed the claim. If it is true and matters, it should be stated again with a source. The 250 per minute figure is the portal's own setting, not Mapline's limit.
