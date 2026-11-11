I updated docs/limits.md to match the code. No code was changed.

Corrections made:
- Search: 50 results per page is now 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout is now 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. The doc now also states the portal's configured rate of 250 lookups a minute (GEOCODE_REQUESTS_PER_MINUTE).
- Account export: the hour (02:00 UTC) was already correct. The doc said deleted accounts are left out of the export, but export_accounts in app/export.py writes every account it receives, including deleted ones, with a `deleted` column. The doc now says so.

Conflicts you need to decide on (I did not resolve them, since they require a product or code decision):
1. Privacy policy: section 4 requires deleted accounts to be left out of the export, and the current export code does not filter them. The doc keeps the policy requirement as written and records the actual behaviour. The code needs a filter, or the policy needs a different basis.
2. Mapline rate: the portal is configured for 250 lookups a minute, but the doc keeps Mapline's free-tier limit of 100 requests a minute per API key. If the account is on the free tier, the configured rate exceeds the quota. Confirm the plan, or lower GEOCODE_REQUESTS_PER_MINUTE.

No reason was given in the repository for the 250/min rate or the 10-second timeout, so I recorded only the values.
