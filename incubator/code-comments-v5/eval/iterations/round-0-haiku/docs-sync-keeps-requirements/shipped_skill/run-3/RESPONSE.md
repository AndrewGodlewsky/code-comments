I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:
- Search: 50 results per page is now 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout is now 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. I also added that the portal's configured rate is 250 lookups a minute, matching GEOCODE_REQUESTS_PER_MINUTE.
- Account export: the old line said deleted accounts are left out. The code does not do that. export_accounts writes every account and sets the `deleted` column. I now say deleted accounts are included, with `deleted` set to True. The 02:00 UTC schedule already matched EXPORT_HOUR_UTC and is unchanged.

Items that need your decision:
1. Privacy conflict: section 4 of the privacy policy, as cited in the doc, requires deleted accounts to be left out of the export. The code includes them. I kept the policy statement as written and did not reword it to fit the code. Someone needs to decide whether the export code or the policy wording is right.
2. Rate conflict: Mapline's free tier allows 100 requests a minute per key, but the portal is configured to send 250 a minute. I kept the vendor fact as written. In geocode.py, MIN_INTERVAL is defined from the 250 rate, but lookup() never uses it, so nothing in the code enforces the rate. Please confirm the intended rate and whether a limiter is missing.
3. Missing reason: I did not find a reason for the 10 second timeout change or the 250 rate in any test or doc I read. The doc now states the configured values without a reason. If a reason exists, please send it so it can be recorded.
