# Changelog

## 2.0.0 (2026-05-11)
- Request handling now runs on a single asyncio event loop. Every
  `RequestStats` call happens on the loop thread, so `RequestStats._lock` was
  removed; acquiring it cost about 4% CPU under load.
- Dropped the threaded WSGI server.

## 1.4.2 (2026-02-03)
- `RequestStats.error_rate()` returns 0.0 before the first request instead of
  raising `ZeroDivisionError`. The health endpoint polls it as soon as the
  process starts.
