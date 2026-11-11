I brought docs/limits.md in line with the code. No code was changed.

Changes made to docs/limits.md:
- Search page size: 50 to 100 results per page (PAGE_SIZE in app/config.py).
- Address lookup timeout: 5 to 10 seconds (GEOCODE_TIMEOUT_SECONDS in app/config.py).
- Export deleted accounts: the doc said deleted accounts are left out of the export. app/export.py writes every account it is given, with a `deleted` column, and nothing in this repo filters them out. The doc now says so.

Items that need your attention:
1. Rate limit conflict. The code sends up to 250 geocoding lookups a minute (GEOCODE_REQUESTS_PER_MINUTE), but Mapline's free tier allows 100 requests a minute per API key. I kept the free-tier fact as written and added a line stating the configured rate. Either the portal's rate or the plan needs to change.
2. Privacy policy conflict. Section 4 of the privacy policy requires deleted accounts to be left out of the export. This repo does not do that. If filtering happens upstream of export_accounts, I could not verify it from here. Please confirm, because the export may be non-compliant as written.
3. Missing rationale. I could not find a reason for the 250 requests-a-minute setting in the repo, so I did not add one. Please tell me if the setting was chosen deliberately to match a plan.

The 02:00 UTC export time already matched EXPORT_HOUR_UTC, so I left that line unchanged.
