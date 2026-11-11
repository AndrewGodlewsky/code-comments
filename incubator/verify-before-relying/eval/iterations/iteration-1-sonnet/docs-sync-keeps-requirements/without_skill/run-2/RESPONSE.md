I updated docs/limits.md to match the code and changed no code.

Changes:
- Search page size: 50 -> 100 (`PAGE_SIZE`).
- Geocode timeout: 5 s -> 10 s (`GEOCODE_TIMEOUT_SECONDS`).
- Geocode rate: the doc quoted Mapline's free tier (100/min). The portal is configured for 250/min (`GEOCODE_REQUESTS_PER_MINUTE`), so I documented that. The 100/min free-tier claim is not in this repo and I could not verify it, so I left a note to check it. 250 exceeds 100, so the portal could be over that limit if the claim is true.
- Export time: 02:00 UTC was already correct.

Needs your decision:
- The doc said deleted accounts are left out of the export, per section 4 of the privacy policy. The code does not do that: `export_accounts` writes every account passed in, with a `deleted` column. I kept the privacy requirement in the doc, since it is a requirement and not just a description, and added a note that the code does not currently meet it. This looks like a compliance gap that needs a code fix, which I did not make. If deleted accounts are filtered upstream of `export_accounts`, tell me and I will reword the note.

Also note: tests/test_portal.py still expects a page size of 100 in one assertion but a page 3 slice of 200-250 (50 results) in another. I did not touch it.
