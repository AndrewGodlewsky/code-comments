I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:
- Search: 50 results per page becomes 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout becomes 10 seconds, matching GEOCODE_TIMEOUT_SECONDS. I added that the portal sends up to 250 lookups a minute, matching GEOCODE_REQUESTS_PER_MINUTE.
- Account export: the nightly time of 02:00 UTC was already correct. I added the CSV columns and corrected the deleted-accounts statement, which the code contradicts (see below).

Conflicts for you to decide on. I did not change code to resolve them:
1. Privacy policy. app/export.py writes every account, including deleted ones, with a `deleted` column. Nothing in the repo filters them out. The privacy policy (section 4, as cited in the old doc) requires deleted accounts to be left out. The doc now states the actual behaviour and names the conflict. The export code or its caller needs a fix, or the policy needs review.
2. Rate limit. The portal is configured for 250 lookups a minute, but the Mapline free tier allows 100 requests a minute per API key. I kept the free-tier statement as written, since it is a vendor fact. If the portal is on the free tier, it exceeds that quota. Please confirm which plan applies.
3. Enforcement. MIN_INTERVAL in app/geocode.py is defined but never used, so nothing in the repo enforces the 250/min rate. I did not document enforcement. Please confirm whether a limiter is planned.
