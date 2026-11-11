I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:
- Search: 50 results per page is now 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the lookup timeout is now 10 seconds (was 5), matching GEOCODE_TIMEOUT_SECONDS. I added that the portal sends at most 250 lookups a minute, matching GEOCODE_REQUESTS_PER_MINUTE. The Mapline free-tier sentence is unchanged, since it describes an outside limit.
- Account export: the 02:00 UTC schedule already matched EXPORT_HOUR_UTC and is unchanged. The claim that deleted accounts are left out was false. app/export.py writes every account it is given and marks deleted ones with True in the `deleted` column. I rewrote that sentence to describe this.

Two conflicts need your decision:
1. Privacy policy: the doc said deleted accounts are excluded "as section 4 of the privacy policy requires". The code includes them. If section 4 really requires exclusion, the export code is non-compliant. Someone needs to either add the filter or confirm the requirement no longer applies. I did not change the code.
2. Rate limit: the portal sends 250 lookups a minute, but Mapline's free tier allows 100 requests a minute per API key. Unless the key is on a paid tier, the portal will exceed the free-tier limit. I left the free-tier fact as written.

Also, the reason for the 250/min rate and the 10-second timeout is not recorded anywhere in the repo, so I did not add one.
