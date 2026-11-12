I updated docs/limits.md to match the code. No code was changed.

Changes made:
- Search: 50 results per page changed to 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout changed from 5 to 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. The doc now states the portal's configured rate of 250 lookups a minute (GEOCODE_REQUESTS_PER_MINUTE). The Mapline free-tier line (100 requests a minute per key) is unchanged, since it is a vendor fact.
- Account export: the doc said deleted accounts are left out of the export. export_accounts() writes every account and includes a `deleted` column, so the doc now says deleted accounts are included with deleted set to True. The nightly 02:00 UTC time was already correct and is unchanged.

Items that need your decision:
1. Privacy policy conflict: the old line said deleted accounts are left out "as section 4 of the privacy policy requires". The code does not do that. I removed the policy clause because it can no longer be true of this code. I could not check the policy itself, since it is not in this repository. Either the export should filter deleted accounts, or section 4 of the policy and this doc need review. This may be a compliance issue, so please check it.
2. Rate limit conflict: the code sends up to 250 lookups a minute, but Mapline's free tier allows 100 a minute per key. If the portal runs on the free tier, it will exceed the quota.
3. Rate limit not enforced: MIN_INTERVAL in app/geocode.py is defined but never used, and lookup() does not sleep or throttle. The doc describes the configured rate, not an enforced one. Either add the throttle or change the doc wording.
