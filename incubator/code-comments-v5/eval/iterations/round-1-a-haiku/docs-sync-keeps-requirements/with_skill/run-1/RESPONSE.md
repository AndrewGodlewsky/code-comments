I updated docs/limits.md to match the code. No code files were changed.

What changed in docs/limits.md:
- Search: 50 results per page is now 100, matching `PAGE_SIZE` in app/config.py.
- Address lookups: the doc now says the portal paces lookups at 250 per minute (`GEOCODE_REQUESTS_PER_MINUTE`), and the timeout is 10 seconds, not 5 (`GEOCODE_TIMEOUT_SECONDS`).
- Account export: the nightly time of 02:00 UTC still matches `EXPORT_HOUR_UTC`. The old sentence said deleted accounts are left out of the export, but export_accounts writes every account and marks deleted ones in the `deleted` column. I corrected that description.
- I added the config constant names next to each value so the next editor can find the source.

Conflicts that need your decision:
1. Geocoding rate: the portal paces lookups at 250 per minute, but Mapline's free tier allows 100 requests a minute per API key. At the configured rate, the portal will exceed the free-tier quota. I kept Mapline's quota as its own sentence and did not change it. Either the rate in app/config.py needs to drop to 100 or below, or the account plan needs to cover 250 per minute.
2. Deleted accounts in the export: section 4 of the privacy policy requires that deleted accounts be left out of the export. The code does not do that. export_accounts includes deleted accounts. I kept the policy requirement as written and did not rewrite it to fit the code. The export code needs a fix, or the policy wording needs review. I did not change code, as you asked.

Also, the export is described as going to the analytics warehouse, and the code and tests do not show any filtering of deleted accounts, so the conflict above is the only open item I found.
