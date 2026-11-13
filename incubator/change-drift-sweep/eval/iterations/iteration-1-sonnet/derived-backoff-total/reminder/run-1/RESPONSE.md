send_alert now makes six attempts (MAX_ATTEMPTS 4 -> 6 in alerts/config.py). That is the first try plus five retries, with waits of 1, 2, 4, 8 and 16 s. I did not run the tests.

Comments and docs that stated the old value or figures derived from it, now corrected:
- alerts/sender.py module docstring: "at most four attempts" -> "six".
- alerts/sender.py wait comment: waits of 1, 2, 4, 8 and 16 s, drop about 31 s after the first try (was 1, 2, 4 and about 7 s).
- alerts/worker.py docstring: a 40-alert backlog in a full outage takes about 21 minutes (40 x 31 s = 1240 s), was "under five minutes".
- docs/oncall.md: drop about 31 seconds after the alert was raised (was seven); a 50-alert storm sends at most 300 POSTs (was 200).
- docs/runbooks/gateway-maintenance.md: the sender retries each alert five times (was three).

Left alone: the 7-day outbox retention in config.py and docs/oncall.md, which is unrelated to the attempt count. The tests use MAX_ATTEMPTS, so they follow the new value.

Mismatches not caused by my change: none found.

Side effect to know about: in a full outage the worker now holds each alert about 31 s instead of 7 s, so the outbox backs up about 4.4 times slower than before.
