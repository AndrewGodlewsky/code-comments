# Changelog

## 2026-09-14
- Raised the response cache TTL from one minute to five minutes to cut load on
  the origin servers during peak traffic. Staleness of up to five minutes was
  approved by the product owner.

## 2026-06-02
- Switched the cache clock to `time.monotonic` after an NTP correction expired
  every entry at once.
