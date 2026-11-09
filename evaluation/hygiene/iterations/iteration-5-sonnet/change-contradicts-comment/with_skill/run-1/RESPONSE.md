I raised the limit to 250 requests a minute, but this is above Geoway's quota as the code documents it. Please check before deploying.

`geo/limits.py` still says Geoway's free tier allows 100 requests a minute per API key, and that going over returns HTTP 429 for the rest of that minute. I left that comment as written because it describes Geoway's quota, not our setting. At 250 a minute you will probably hit those 429s unless the key is on a higher tier. I don't know whether it is, so I didn't change the quota note.

What changed:
- `geo/limits.py`: `REQUESTS_PER_MINUTE` is now 250. The quota comment above it is unchanged.
- `geo/client.py`: the module docstring now says the client sends at most 250 requests a minute.
- `docs/geocoding.md`: now says at most 250 requests a minute.

The throttle code and the tests read the constant, so they needed no edits. I haven't run the tests.

Question: is the Geoway plan or key on a tier that allows 250 a minute? If so, tell me the new quota and where it comes from, and I'll update the quota comment in `geo/limits.py`. If not, the limit should go back to 100 or the plan needs upgrading.
