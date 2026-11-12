I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:
- Search page size: 50 changed to 100, per PAGE_SIZE in app/config.py (the test in tests/test_portal.py also expects 100).
- Lookup timeout: 5 seconds changed to 10, per GEOCODE_TIMEOUT_SECONDS in app/config.py.
- Address lookups: added the portal's configured rate of 250 a minute and the 0.24-second minimum spacing, per GEOCODE_REQUESTS_PER_MINUTE and MIN_INTERVAL in app/geocode.py.
- Account export: the doc said deleted accounts are left out of the export. Nothing in this repository does that. export_accounts in app/export.py writes every account it is passed, with a `deleted` column. I replaced the claim with what the code does and kept the privacy-policy requirement as stated.
- The nightly export time (02:00 UTC) already matched EXPORT_HOUR_UTC and was left as it was.

Conflicts for you to resolve (not fixed, because they need a decision or a fact I cannot check here):
1. Mapline rate limit: the doc keeps "Mapline's free tier allows 100 requests a minute per API key", which I could not verify. The portal is configured to send 250 a minute, so if that vendor limit is correct, the portal exceeds it on the free tier. Either the configured rate or the vendor limit needs checking.
2. Deleted accounts: section 4 of the privacy policy requires deleted accounts to be left out of the export, but this repository never filters them. Either the caller filters before calling export_accounts (I cannot see the caller in this repository), or export_accounts needs a filter. I did not change code.
