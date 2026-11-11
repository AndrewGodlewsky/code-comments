I updated docs/limits.md to match the code. No code was changed.

What changed:
- Search page size: the doc said 50 results per page. `PAGE_SIZE` is 100, and the test in `tests/test_portal.py` agrees.
- Geocoding rate: the doc said Mapline's free tier allows 100 requests a minute. The code sends up to `GEOCODE_REQUESTS_PER_MINUTE` = 250 a minute. I rewrote the section to state the portal's configured rate and the minimum gap between lookups (0.24 s).
- Geocoding timeout: the doc said 5 seconds. `GEOCODE_TIMEOUT_SECONDS` is 10.
- Export time: 02:00 UTC was already correct and is unchanged.

Needs your decision: the account export does not leave out deleted accounts. `app/export.py` writes every account and includes a `deleted` column. The old doc said deleted accounts are left out "as section 4 of the privacy policy requires." I did not keep that claim, because the code does not do it. I described the actual behavior instead. If the privacy policy really does require deleted accounts to be excluded, the export code is non-compliant and needs a fix. That is a code change, so I left it alone.

Also check: the 250/min rate is higher than the 100/min free tier the old doc cited. If the portal is on the free tier, the configured rate would exceed Mapline's limit. I could not verify which tier the account is on from the repository.
