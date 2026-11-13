I updated two descriptions in `docs/limits.md` and changed no code. Two other lines conflict with the code, and I left them as written.

**Corrected (descriptions that were wrong)**
- Search: the doc said 50 results per page. `PAGE_SIZE = 100` in `app/config.py`, and `test_pages_hold_page_size_results` pins 100. It now says 100.
- Address lookups: the doc said a lookup gives up after 5 seconds. `GEOCODE_TIMEOUT_SECONDS = 10`, and `app/geocode.py` `lookup` passes it as the request timeout. It now says 10 seconds.

**Checked and left unchanged**
- The nightly export at 02:00 UTC is true. `EXPORT_HOUR_UTC = 2`, and `next_export` and its tests agree.

**Kept as written, but the code breaks them (possible bugs)**
- Account export, "Deleted accounts are left out of the export, as section 4 of the privacy policy requires." This is a requirement. `export_accounts` in `app/export.py` writes every account it is given and has no filter. `deleted` is just an exported column, and the test pins that. Unless callers filter deleted accounts beforehand (I did not check this, because it is outside the files here), deleted accounts are being exported.
- Address lookups, "Mapline's free tier allows 100 requests a minute per API key." This is an outside fact about Mapline. `GEOCODE_REQUESTS_PER_MINUTE = 250` in `app/config.py`, and `MIN_INTERVAL` in `app/geocode.py` is derived from it. If the portal is on the free tier, the configured rate is 2.5 times the limit. The doc's sentence stays as written. I also did not verify Mapline's actual limit.
