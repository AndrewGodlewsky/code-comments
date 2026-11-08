I raised REQUESTS_PER_MINUTE to 250 and updated the client docstring and
docs/geocoding.md to match.

One conflict to check before this ships: the comment in geo/limits.py says Geoway's
free tier allows 100 requests a minute per key and returns HTTP 429 above that. 250 is
over that quota. If your account is on a higher plan, tell me its limit and I'll
update the comment; if not, the extra requests will be rejected.
