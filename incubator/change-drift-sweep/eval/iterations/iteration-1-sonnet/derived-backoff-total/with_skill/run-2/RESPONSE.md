send_alert now makes six attempts (MAX_ATTEMPTS 4 -> 6 in alerts/config.py). Tests pass.

Because the backoff doubles, the five waits are 1, 2, 4, 8 and 16 s, so a dropped alert now takes 31 s (was 7 s). Several prose figures stated the old behaviour, so I corrected them:

- alerts/sender.py: module docstring "at most four attempts" -> "six"; comment "Waits of 1, 2 and 4 s ... about 7 s" -> "1, 2, 4, 8 and 16 s ... about 31 s".
- alerts/worker.py: "a backlog of 40 alerts takes under five minutes to clear" -> "about 21 minutes" (40 x 31 s = 1240 s; it was 40 x 7 s = 280 s).
- docs/oncall.md: "drops the alert about seven seconds" -> "about 31 seconds"; "50 alerts sends at most 200 POSTs" -> "300 POSTs" (50 x 6).
- docs/runbooks/gateway-maintenance.md: "retries each alert three times" -> "five times" (retries = attempts - 1).

Kept: the 7-day outbox retention (config.py, docs/oncall.md) is unrelated to the retry count. The tests use MAX_ATTEMPTS and BASE_DELAY_S, so they needed no change.

Trade-off: a full outage now holds the worker about four times longer per alert, so draining a backlog is slower (see the worker figure above). No ADRs, changelog, or instruction files were affected, and no drift existed before this change.
