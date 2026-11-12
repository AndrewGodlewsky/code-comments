I updated docs/limits.md to match the code. No code was changed.

Changes:
- Search: 50 results per page is now 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout is now 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. I also added the portal's configured rate: at most 250 lookups a minute, 0.24 seconds apart, matching GEOCODE_REQUESTS_PER_MINUTE and MIN_INTERVAL in app/geocode.py.
- Account export: the 02:00 UTC schedule was already correct. The sentence saying deleted accounts are left out was false. app/export.py includes every account and writes deleted as a column, so deleted accounts appear with deleted set to True. I kept the privacy-policy requirement as written.

Needs your attention:
- Privacy: section 4 of the privacy policy says deleted accounts must be left out of the export, but the export includes them. I did not change the code. Someone needs to decide whether to filter them out or whether the policy is wrong.
- Rate limit: the portal sends up to 250 lookups a minute, but Mapline's free tier allows 100 per API key. Unless the portal runs on a paid tier, Mapline will likely throttle or reject requests above 100 a minute. I kept the vendor fact as written.
- Commented-out code: none found in the files I read.
