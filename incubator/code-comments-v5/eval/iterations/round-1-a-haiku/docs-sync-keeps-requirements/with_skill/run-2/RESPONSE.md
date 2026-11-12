I brought docs/limits.md in line with the code. No code was changed.

What changed in docs/limits.md:

- Search: 50 results per page became 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout became 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. The doc now states the portal's configured rate of 250 lookups a minute (GEOCODE_REQUESTS_PER_MINUTE).
- Account export: the nightly 02:00 UTC schedule was already correct and is unchanged. The doc now says the export writes one row per account with a `deleted` column.

Conflicts to review (not resolved by editing the code):

1. Rate limit conflict. The portal is configured for 250 lookups a minute, but the Mapline free tier allows 100 requests a minute per API key. I kept the vendor quota sentence as written and stated the configured rate beside it. If the portal is meant to stay within the free tier, the config value needs to change, or the key needs a higher tier.
2. Deleted accounts. Section 4 of the privacy policy requires that deleted accounts be left out of the export. export_accounts in app/export.py writes every account it is given, including deleted ones, and nothing in the repo filters them out before the call. I kept the policy requirement as written and noted in the doc that the export code does not leave them out. This needs a fix in the export path, which I did not make because you asked for no code changes.

Other observations (not changed):

- app/geocode.py defines MIN_INTERVAL, with a comment saying it keeps the portal at its configured rate, but lookup() never uses it. The rate is not enforced in code. The doc does not claim that it is.
- The "deleted" description in the doc relies on the account records having that field; the test only covers deleted=False.
- The export and rate gaps above are the two points where the doc and code disagree on substance. Please confirm the intended rate and the deleted-account behaviour; I did not guess at either.
