I updated `docs/limits.md` to match the code. No code was changed.

Corrections made:

- **Search page size:** the doc said 50 results per page. `PAGE_SIZE` in `app/config.py` is 100, so the doc now says 100.
- **Lookup timeout:** the doc said 5 seconds. `GEOCODE_TIMEOUT_SECONDS` is 10, so the doc now says 10.
- **Lookup rate:** the doc said Mapline's free tier allows 100 requests a minute. The code sets the portal's rate to `GEOCODE_REQUESTS_PER_MINUTE = 250`, so the doc now states the 250 limit. I removed the free-tier sentence because nothing in the repo supports it.
- **Export schedule:** the doc said nightly at 02:00 UTC. This matches `EXPORT_HOUR_UTC = 2`, so it is unchanged apart from a reference to the setting.
- **Deleted accounts:** the doc said deleted accounts are left out of the export, as section 4 of the privacy policy requires. The code does not do this. `export_accounts` in `app/export.py` writes every account and includes a `deleted` column. The doc now describes that behaviour.

Please review the deleted-accounts point before anything else. The export sends deleted accounts to the analytics warehouse, and the doc previously said the opposite because of the privacy policy. If section 4 really requires deleted accounts to be excluded, the export code is wrong and needs a fix, which is outside this task. I did not verify the privacy policy, so I have not confirmed what it requires.

Also check the 250 requests a minute setting against Mapline's actual limits. If Mapline's free tier really is 100 a minute, the portal would exceed it at the configured rate. I could not check Mapline's terms from the repo.
