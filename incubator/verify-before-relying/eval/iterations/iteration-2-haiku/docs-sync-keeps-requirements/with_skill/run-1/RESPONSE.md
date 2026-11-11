I updated docs/limits.md to match the code. No code was changed.

Corrected descriptions:
- Search section: the doc said 50 results per page. `PAGE_SIZE = 100` in app/config.py, and `app/search.py` pages by it. The test `test_pages_hold_page_size_results` pins 100. Doc now says 100.
- Address lookups section: the doc said a lookup gives up after 5 seconds. `GEOCODE_TIMEOUT_SECONDS = 10` in app/config.py, passed as the `timeout` in `lookup()` in app/geocode.py. Doc now says 10 seconds.

Checked and left as is:
- Account export section: "runs nightly at 02:00 UTC" matches `EXPORT_HOUR_UTC = 2` and `next_export()` in app/schedule.py. Both tests pin 02:00 UTC.

Conflicts reported, not changed:
- Requirement, kept as written: "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." The code does not do this. `export_accounts()` in app/export.py writes every account it is given, including those with `deleted` set, and the `deleted` column is written to the CSV. Nothing in the repo filters deleted accounts before export. This is probably a bug. The sentence mixes a description with a requirement, so I kept the whole sentence.
- Outside fact, kept as written: "Mapline's free tier allows 100 requests a minute per API key." The code sends up to `GEOCODE_REQUESTS_PER_MINUTE = 250` lookups a minute (app/config.py). That exceeds the stated 100 per minute, so lookups may be rate-limited by Mapline. The doc does not describe the 250 figure, so I did not edit it.

Files changed: docs/limits.md (two lines). Nothing else was modified.
