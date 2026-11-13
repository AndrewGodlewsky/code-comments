I updated docs/limits.md to match the code. No code was changed.

Changes:
- Search: 50 results per page changed to 100, matching PAGE_SIZE in app/config.py.
- Address lookups: timeout changed from 5 to 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. Added that the portal is configured to send up to 250 lookups a minute, matching GEOCODE_REQUESTS_PER_MINUTE.
- Account export: the doc said deleted accounts are left out. app/export.py writes every account with a `deleted` column. I rewrote the line to say so and kept the privacy policy requirement as written.
- Nightly time at 02:00 UTC was already correct and is unchanged.

Conflicts you need to decide on (not resolved by me):
1. Rate limit: the portal is configured for 250 lookups a minute, but Mapline's free tier, as stated in the doc, allows 100 a minute. Either the portal exceeds the free tier or the configured rate or the vendor fact is wrong. I kept the vendor fact as written.
2. Privacy: the export includes deleted accounts, which the doc says section 4 of the privacy policy forbids. This is a compliance gap in the code, not just a stale doc.
3. Unenforced rate: app/geocode.py defines MIN_INTERVAL (about 0.24 s) with a comment saying it keeps the portal at its configured rate, but lookup() never uses it. Nothing in the code spaces out lookups, so the 250/min figure is a setting, not an enforced limit. The doc says "configured to", which is accurate, but the geocode.py comment is false and was left alone since code changes were out of scope.
