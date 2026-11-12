I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:

- Search page size: 50 changed to 100, matching `PAGE_SIZE` in app/config.py.
- Geocoding timeout: 5 seconds changed to 10, matching `GEOCODE_TIMEOUT_SECONDS`.
- Geocoding rate: added that the portal sends at most 250 lookups a minute, matching `GEOCODE_REQUESTS_PER_MINUTE`.
- Account export: removed the claim that deleted accounts are left out, because app/export.py does not filter them. The doc now says they are included with `deleted` set to `True`.
- The nightly export time (02:00 UTC) already matched `EXPORT_HOUR_UTC` and is unchanged, apart from a pointer to the config setting.

Needs your decision:

1. Privacy policy conflict. The old doc said deleted accounts are left out of the export "as section 4 of the privacy policy requires". The code includes them. I did not reinstate the old claim, because that would document a behaviour the code does not have. If the policy really requires exclusion, the export needs a filter (a code change I did not make). If the filter is applied by a caller outside this repository, that caller is not visible here, so please check it.
2. Rate conflict. The doc still says Mapline's free tier allows 100 requests a minute, but the portal is configured to send 250 a minute. If the free tier applies to this key, the portal will exceed it. I left the vendor sentence as written, since I cannot verify it from the repository.
