I updated docs/limits.md to match the code. No code was changed.

Changes:
- Search: 50 results per page is now 100 (`PAGE_SIZE` in `app/config.py`).
- Address lookups: the timeout is now 10 seconds, not 5 (`GEOCODE_TIMEOUT_SECONDS`).
- Address lookups: the rate is now "at most 250 lookups a minute" (`GEOCODE_REQUESTS_PER_MINUTE`). I removed the sentence about Mapline's free tier allowing 100 requests a minute per API key. The code does not establish that figure, and it conflicts with the 250/min the portal is configured to send. If the free-tier limit is real, the 250/min setting may be too high, so please check it against Mapline's plan.
- Account export: the 02:00 UTC schedule still matches (`EXPORT_HOUR_UTC = 2`). I added the config reference.

Needs your attention: the old doc said deleted accounts are left out of the export, as section 4 of the privacy policy requires. The code does not do that. `app/export.py` writes every account it is given and includes a `deleted` column. Nothing in this repo filters deleted accounts before the export is called, so either the caller filters them upstream (not in this repo) or the export includes deleted accounts. I did not keep the privacy-policy claim, because the code does not support it. Please confirm where deleted accounts are filtered, and whether that matches section 4 of the privacy policy. If the filtering is missing, it is a code fix, which I did not make.
