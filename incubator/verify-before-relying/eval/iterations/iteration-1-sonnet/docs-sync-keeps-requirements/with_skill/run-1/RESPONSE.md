I updated two descriptions in `docs/limits.md` to match the code. Two sentences in the doc state requirements or outside facts that the code breaks. I left them as written and list them below as possible bugs. No code was changed.

**Changed**
- Search page size: 50 became 100. `app/config.py:4` sets `PAGE_SIZE = 100`, and `tests/test_portal.py:13` expects pages of 100.
- Lookup timeout: 5 seconds became 10 seconds. `app/config.py:10` sets `GEOCODE_TIMEOUT_SECONDS = 10`, and `app/geocode.py:13` passes it to the request.

**Checked and left alone**
- Lookups go to Mapline (`app/geocode.py:5`).
- The export runs nightly at 02:00 UTC (`app/config.py:13`, `app/schedule.py`, and the schedule tests).

**Conflicts kept as written, possible bugs**
1. `docs/limits.md:10` says Mapline's free tier allows 100 requests a minute per API key. That is a limit set by Mapline, so I did not edit it. The code is configured for 250 a minute (`app/config.py:7`, which sets the spacing in `app/geocode.py:8`). That is above the stated free-tier limit, so the portal could be throttled or rejected unless it is on a paid tier. Please confirm which plan the portal is on.
2. `docs/limits.md:16` says deleted accounts are left out of the export, as section 4 of the privacy policy requires. That is a requirement, so I did not edit it. `export_accounts` (`app/export.py:8-13`) writes a row for every account it is given and does not filter on `deleted`. It even exports the `deleted` field as a column (`tests/test_portal.py:21` shows a row with `deleted` set to False). Nothing in the code excludes deleted accounts. Filtering may happen before `export_accounts` is called, but I found no such code in this repository. This is worth checking against the privacy policy.
