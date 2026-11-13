I updated docs/limits.md to match the code. No code was changed. Two of the updates expose conflicts you need to look at.

Changes that were plain drift:
- Search page size is now 100, not 50 (`PAGE_SIZE` in app/config.py).
- The lookup timeout is now 10 seconds, not 5 (`GEOCODE_TIMEOUT_SECONDS`).
- The 02:00 UTC export time was already correct.

Conflicts:
- **Geocoding rate:** the code is configured for 250 requests a minute (`GEOCODE_REQUESTS_PER_MINUTE`). Mapline's free tier allows 100 a minute per key. I kept the Mapline limit as written, since it is an outside fact, and added the portal's configured 250. If the portal is on the free tier it will exceed the quota. Either the plan or the setting needs to change.
- **Deleted accounts in the export:** the doc said deleted accounts are left out, as the privacy policy requires. The code does not do that. `export_accounts` writes every account, with a `deleted` column. I rewrote the doc to say deleted accounts are included, and I kept the privacy-policy requirement (section 4) as stated. The code does not currently meet it. I did not read the policy itself, so I cannot confirm what section 4 says.

I did not add or change any code comments.
