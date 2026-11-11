send_alert now makes up to six attempts per alert (it was four). The change is `MAX_ATTEMPTS = 6` in `alerts/config.py`. I did not run the tests.

Because the waits double, a dropped alert now takes longer to give up on:

- Waits are 1, 2, 4, 8 and 16 s, so an alert is dropped about 31 s after the first try (it was about 7 s).
- In a full outage, a backlog of 40 alerts holds the worker for about 21 minutes (it was under five).
- A storm of 50 alerts now sends at most 300 POSTs to the gateway (it was 200).

I updated the text that stated the old numbers: the docstring and comment in `alerts/sender.py`, the backlog estimate in `alerts/worker.py`, `docs/oncall.md`, and the runbook in `docs/runbooks/gateway-maintenance.md`. The runbook now says five retries instead of three. The tests read `MAX_ATTEMPTS`, so they needed no edits.

If the 21-minute drain is too slow during a real outage, a smaller base delay or a cap on the wait would keep six attempts while shortening the total. I left the backoff unchanged.
