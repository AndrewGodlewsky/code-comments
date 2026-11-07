# Token issuer changelog

## 2026-10-15

- Every token response now includes `expires_at`: the expiry as Unix time in
  seconds (UTC).
- Token lifetimes are now configured per client and range from 15 minutes to
  12 hours. Clients must not assume a fixed lifetime.
- `issued_at` is deprecated and will be removed from responses in a later
  release.

## Unchanged

- The API gateway still validates tokens against its own clock, which may run
  up to 60 seconds ahead of client clocks.
