I brought docs/limits.md in line with the code. No code was changed.

Changes to docs/limits.md:
- Search: 50 results per page changed to 100, the value of PAGE_SIZE in app/config.py.
- Address lookups: timeout changed from 5 seconds to 10, the value of GEOCODE_TIMEOUT_SECONDS.
- Address lookups: added the portal's configured limit of 250 lookups a minute, and that lookup() does not enforce it.
- Account export: the claim that deleted accounts are left out was false. export_accounts in app/export.py writes every account it is given, with deleted accounts marked in the deleted column. The doc now says so.
- Unchanged: the 02:00 UTC nightly export time (matches EXPORT_HOUR_UTC = 2) and the Mapline free tier quota of 100 requests a minute, which the code cannot confirm.

Issues that need your decision (not changed, since the code stays as it is):
1. Privacy gap: section 4 of the privacy policy requires deleted accounts to be left out of the export, but export_accounts does not filter them. Unless the caller filters them out (no caller is in this repository), the nightly export includes deleted accounts. The doc keeps the policy requirement as written and states the gap.
2. Rate conflict: the portal is configured to send 250 lookups a minute, but Mapline's free tier allows 100 requests a minute per key. Also, lookup() never waits, so the portal does not enforce its own limit.
3. False code comment: the comment on MIN_INTERVAL in app/geocode.py says it keeps the portal at its configured rate, but MIN_INTERVAL is never used. Left as is because this is a code change. Either the rate limiting should be implemented, or the comment should be corrected.
