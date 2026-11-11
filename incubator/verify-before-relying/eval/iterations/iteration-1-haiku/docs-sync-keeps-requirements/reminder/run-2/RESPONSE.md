I updated `docs/limits.md` to match the code. No code was changed.

Corrections made, each checked against `app/` and `tests/test_portal.py`:

- Search: the doc said 50 results per page. `PAGE_SIZE` is 100, and the paging test confirms 100.
- Address lookups: the doc said a lookup gives up after 5 seconds. `GEOCODE_TIMEOUT_SECONDS` is 10.
- Account export: the schedule (02:00 UTC) was already correct. I added the config name and tied it to `next_export`'s test.
- Added the configured rate of 250 lookups a minute, which the doc did not mention.

Conflicts for you to decide on. I kept the stated facts as written and did not change the requirement:

1. Deleted accounts in the export. The doc says deleted accounts are left out, as section 4 of the privacy policy requires. `export_accounts` in `app/export.py` writes every account it is given and includes a `deleted` column. Nothing in this repository filters them out. The doc now says that, and it states the policy requirement and that the current code does not meet it. If the caller filters upstream, that code is not in this repo, so please confirm.
2. Mapline rate limit. The doc keeps the free-tier limit of 100 requests a minute. The portal is configured for 250 a minute, so it exceeds that limit. `app/geocode.py` defines `MIN_INTERVAL` but `lookup()` never uses it, so the portal does not throttle at all. The doc says so.

Files changed: `docs/limits.md` and this `RESPONSE.md`.
