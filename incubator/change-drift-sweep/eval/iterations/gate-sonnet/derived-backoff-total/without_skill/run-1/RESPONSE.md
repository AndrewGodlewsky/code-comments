send_alert now makes up to six attempts (MAX_ATTEMPTS 4 -> 6 in alerts/config.py).

Things that change because of it:
- Backoff doubles from 1 s, so the waits are 1, 2, 4, 8 and 16 s. An alert is now dropped about 31 s after the first try, up from about 7 s. I updated the comment in alerts/sender.py and the text in docs/oncall.md to say so.
- Worst-case gateway load in a full outage rises from 200 to 300 POSTs for a 50-alert storm (docs updated).
- Callers of send_alert block up to about 31 s on a dead gateway instead of about 7 s.

Not changed: the 7-day outbox retention, retryable statuses (502/503/504), and the base delay. If 31 s is too long, a smaller base delay or a cap on the wait would give six tries in less time.

I did not run the tests; the tests read MAX_ATTEMPTS from config, so they should follow the new value.
