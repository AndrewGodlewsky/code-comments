I updated docs/limits.md to match the code. No code files were changed.

Changes made:
- Search: 50 results per page changed to 100, matching PAGE_SIZE in app/config.py.
- Address lookups: the timeout changed from 5 seconds to 10, matching GEOCODE_TIMEOUT_SECONDS. I added that the portal sends up to 250 lookups a minute, matching GEOCODE_REQUESTS_PER_MINUTE.
- Account export: the nightly 02:00 UTC schedule was already correct (EXPORT_HOUR_UTC = 2). The claim that deleted accounts are left out was false: app/export.py writes every account and has a `deleted` column. I corrected that sentence to describe the code, and kept the privacy policy requirement as its own sentence.

Conflicts that need your decision (not resolved in the doc or code):
1. The portal's configured rate of 250 lookups a minute is above Mapline's free-tier limit of 100 requests a minute per API key. Either the rate or the plan needs to change.
2. Section 4 of the privacy policy requires deleted accounts to be left out of the export, but app/export.py includes them and nothing filters them out. The export does not meet that requirement. I left the requirement as written and did not change the code, as you asked.
