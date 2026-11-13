I updated `docs/limits.md` to match the code. No code was changed.

Changes:

- **Search page size:** the doc said 50 results per page. `PAGE_SIZE` in `app/config.py` is 100, so the doc now says 100.
- **Address lookup timeout:** the doc said 5 seconds. `GEOCODE_TIMEOUT_SECONDS` is 10, so the doc now says 10 seconds.
- **Address lookup rate:** the doc gave only Mapline's free-tier limit of 100 a minute. The portal is configured to send at most 250 lookups a minute (`GEOCODE_REQUESTS_PER_MINUTE`), so the doc now states that. I kept the free-tier sentence because the code cannot confirm it.
- **Account export:** the nightly time of 02:00 UTC matches `EXPORT_HOUR_UTC`, so it is unchanged. The doc said deleted accounts are left out of the export, but `app/export.py` writes every account with a `deleted` column and does not filter. The doc now describes that behavior.

Needs your decision:

- **Deleted accounts in the export.** The code includes deleted accounts, but section 4 of the privacy policy says they must be left out. I documented what the code does and noted the conflict in the doc. If the filtering happens in a caller outside this repository, the doc is wrong and should be restored. If not, the export needs a code change before the next run. I did not change the code.
- **Mapline free tier.** If that free-tier limit applies to this account, the portal's 250 lookups a minute would exceed it. Please confirm the plan and key tier.
