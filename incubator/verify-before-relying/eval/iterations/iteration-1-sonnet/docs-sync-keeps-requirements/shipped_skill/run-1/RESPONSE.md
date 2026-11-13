I updated `docs/limits.md` to match the code. I changed no code.

Changes:
- Search page size: 50 -> 100 (`PAGE_SIZE`).
- Lookup timeout: 5 -> 10 seconds (`GEOCODE_TIMEOUT_SECONDS`).
- Added the configured lookup rate: 250 a minute (`GEOCODE_REQUESTS_PER_MINUTE`).
- Export schedule (02:00 UTC) was already correct and is unchanged.
- Export of deleted accounts: the doc said they are left out. The code does not do that. `export_accounts` writes every account it is given and includes a `deleted` column. I rewrote the sentence to say what the code does and kept the privacy-policy requirement as written.

Problems for you to check:
- The portal is configured for 250 lookups a minute, but Mapline's free tier allows only 100 a minute per API key. I left Mapline's limit as written because it is an outside fact. At 250 a minute the portal would exceed that limit on the free tier. Is the portal on a paid tier, or should the rate be lowered?
- Deleted accounts may appear in the export, which conflicts with section 4 of the privacy policy. I only saw `export_accounts`, not its caller. If the caller filters deleted accounts out, the doc's last line should be adjusted. If it does not, this is a compliance gap in the code.
- No reason is recorded in the repository for the changes to the page size, timeout or rate. I documented only the current values.
