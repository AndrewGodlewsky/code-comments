I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:
- Search: 50 results per page changed to 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout changed from 5 seconds to 10, matching GEOCODE_TIMEOUT_SECONDS. The rate is now stated as the portal's configured 250 lookups a minute (GEOCODE_REQUESTS_PER_MINUTE). I removed the Mapline free-tier claim (100 requests a minute per key), because this repo does not show which Mapline plan the portal uses.
- Account export: the 02:00 UTC schedule still matches EXPORT_HOUR_UTC. The claim that deleted accounts are left out was wrong. export_accounts writes every account it is given and marks deleted ones in a `deleted` column, so the doc now says that.

Items that need a human decision (not resolved by the doc edit):
1. Privacy policy: the old doc said deleted accounts are excluded "as section 4 of the privacy policy requires". The export code here does not exclude them. If the policy still requires exclusion, either the filter is applied somewhere outside this repo (I could not check, since the caller is not in this repo) or the export is non-compliant. Please check before relying on the doc's new wording.
2. Geocoding rate: nothing enforces the 250 per minute setting. geocode.py computes MIN_INTERVAL but never uses it, so the portal does not throttle. If Mapline's free tier really is 100 requests a minute, as the old doc said, the portal would exceed it. Please confirm the plan limit and either add throttling or correct the config.
