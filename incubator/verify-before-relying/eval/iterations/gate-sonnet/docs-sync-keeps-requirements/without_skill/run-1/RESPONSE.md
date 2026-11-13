I updated docs/limits.md for the three values that had drifted. I changed no code.

- Search: 50 results per page is now 100 (`PAGE_SIZE` in app/config.py).
- Address lookups: the portal is configured to send 250 lookups a minute (`GEOCODE_REQUESTS_PER_MINUTE`). I replaced the old "100 requests a minute" line with that.
- Address lookups: the timeout is now 10 seconds (`GEOCODE_TIMEOUT_SECONDS`), not 5.
- Export: the 02:00 UTC schedule already matches the code, so I left it alone.

Two things need your attention.

1. **The export does not leave out deleted accounts.** docs/limits.md says deleted accounts are left out, as section 4 of the privacy policy requires. `export_accounts` in app/export.py writes every account and includes a `deleted` column. Nothing filters them out, and the tests don't check for it. I kept the sentence in the doc because it is a policy requirement, and rewording it to match the code would hide a possible compliance gap. Either the export needs a filter, or someone needs to confirm what the policy actually requires and fix the doc.

2. **The configured rate is above the Mapline free tier I removed from the doc.** I took out the claim that the free tier allows 100 requests a minute per key, because I can't verify it from this repo and it no longer described the portal. The configured 250 a minute would exceed that limit if it is still true, so check it against your Mapline plan.
