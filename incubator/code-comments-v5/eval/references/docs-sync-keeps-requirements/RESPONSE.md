I updated two lines in docs/limits.md to match the code: search returns 100 results per page
(`PAGE_SIZE = 100`), and a lookup gives up after 10 seconds (`GEOCODE_TIMEOUT_SECONDS = 10`).
I changed no code.

Two lines I left as written, because they are not descriptions of our code, and the code
breaks both:

- The doc says deleted accounts are left out of the export, as section 4 of the privacy
  policy requires. `export_accounts` in app/export.py writes every account it is given,
  deleted ones included. That looks like a privacy bug in the code, not an error in the doc.
- The doc says Mapline's free tier allows 100 requests a minute per API key, but
  `GEOCODE_REQUESTS_PER_MINUTE` is 250. Unless the account is on a paid plan, lookups above
  100 a minute will be refused.

Tell me if you want either of these fixed in the code.
