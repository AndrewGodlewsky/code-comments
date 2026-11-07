# Let clients choose retries per request

API clients can now send an `X-Retries` header to pick the retry count for a
single request. Add `retries_for_request(settings, headers)` to `policy.py`.
`headers` is a dict mapping header names to string values.

- Without an `X-Retries` header, return what `resolve_retries(settings)` gives
  today.
- With one, its value is the client's override and follows the same rules as
  an override passed to `resolve_retries`.
- A value that isn't a whole number raises `ValueError`.

`resolve_retries` itself should keep working as it does now.
