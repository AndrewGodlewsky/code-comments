I updated docs/limits.md to match the code. I changed no code.

Changes, all from app/config.py:
- Search now returns 100 results per page (was 50). `PAGE_SIZE = 100`, and the test agrees.
- Address lookups now time out after 10 seconds (was 5). `GEOCODE_TIMEOUT_SECONDS = 10`.
- I added a line saying the portal sends at most 250 lookups a minute. `GEOCODE_REQUESTS_PER_MINUTE = 250`.
- The nightly export at 02:00 UTC was already correct (`EXPORT_HOUR_UTC = 2`).

Two things need your attention:
1. The doc says Mapline's free tier allows 100 requests a minute per key. The code is configured for 250 a minute. I left the tier sentence alone because I can't check Mapline's limits from here. If the portal is on the free tier, 250 a minute exceeds it. Either the tier claim is out of date or the config is too high.
2. The doc says deleted accounts are left out of the export, as the privacy policy requires. The code does not do that. `export_accounts` in app/export.py writes every account, and "deleted" is just one of the exported columns. I kept the sentence because it states a requirement, and rewriting it to describe the current behaviour would hide a likely privacy-policy gap. The code probably needs a fix to filter deleted accounts, but I was told not to change code. Please decide whether to fix the export or revise the requirement.
