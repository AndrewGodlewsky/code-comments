I brought docs/limits.md in line with the code. No code was changed.

What changed in docs/limits.md:

- Search: 50 results per page is now 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout is now 10 seconds (GEOCODE_TIMEOUT_SECONDS), not 5.
- Address lookups: the rate is now the portal's configured 250 lookups a minute (GEOCODE_REQUESTS_PER_MINUTE). The old "Mapline's free tier allows 100 requests a minute" sentence is removed because nothing in the code states it, and I could not verify it.
- Account export: the 02:00 UTC schedule was already correct and is unchanged.
- Account export: the old sentence said deleted accounts are left out of the export, citing section 4 of the privacy policy. app/export.py writes every account it receives, including deleted ones (a `deleted` column records the flag), and nothing in the code filters them out. I replaced the sentence with what the code does.

Please check the export item before this doc is relied on. If the privacy policy really requires deleted accounts to be excluded, the export code does not do that, and the nightly job may be filtering them somewhere outside this repository. I could not see a caller in this repository, so I could not confirm either way. I did not add the privacy claim back, because the doc should describe the current code.

Also check the rate item: if Mapline's free tier is really 100 requests a minute, the portal's configured 250 a minute is above it. That is a question about the configured value, so I left the code alone.
