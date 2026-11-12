I updated docs/limits.md to match the code. I did not change any code.

Changes made:
- Search: the page size is 100, not 50 (`PAGE_SIZE` in `app/config.py`).
- Address lookups: the timeout is 10 seconds, not 5 (`GEOCODE_TIMEOUT_SECONDS`). I also added that the portal is configured for 250 lookups a minute (`GEOCODE_REQUESTS_PER_MINUTE`).
- Account export: the 02:00 UTC schedule was already correct. I added the config name to it.
- Account export: the old text said deleted accounts are left out. `export_accounts` in `app/export.py` writes every account and sets `deleted` to True for deleted ones. I corrected the doc to say so.

Conflicts for you to decide on. I did not resolve these in code.
1. Privacy policy: section 4 requires deleted accounts to be left out of the export, but the code includes them. The doc now says so. This is a compliance gap, not just a doc error. Someone needs to decide whether the code or the policy changes.
2. Mapline rate limit: the portal is configured for 250 lookups a minute, but the free tier allows 100 a minute per key. I kept the vendor figure as written, since I cannot verify it. If the free tier applies, the portal's configured rate would exceed it.
3. Rate spacing: `MIN_INTERVAL` in `app/geocode.py` (60 / 250 seconds) is defined but `lookup()` never uses it, so the portal does not enforce the 250 a minute rate. The doc does not claim that it does. If you want the spacing enforced, that is a code change for you to approve.
