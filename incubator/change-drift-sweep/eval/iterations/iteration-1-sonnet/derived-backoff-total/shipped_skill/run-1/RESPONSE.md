send_alert now makes up to six attempts (`MAX_ATTEMPTS` is 6 in `alerts/config.py`). The doubling waits are unchanged, so an alert is dropped about 31 s after the first try (1+2+4+8+16 s), up from about 7 s. I did not run the tests.

I also corrected the text that described the old four-attempt behaviour:
- `alerts/sender.py`: the module docstring now says six attempts, and the wait comment lists 1, 2, 4, 8 and 16 s and about 31 s.
- `alerts/worker.py`: the backlog estimate for 40 alerts in a full outage was "under five minutes" and is now about 21 minutes (40 x 31 s).
- `docs/oncall.md`: the drop time is about 31 s, and a 50-alert storm sends at most 300 POSTs instead of 200.
- `docs/runbooks/gateway-maintenance.md`: the sender retries five times, not three.

Things to check:
- In a full outage the worker is blocked much longer per alert, so later alerts in the outbox wait about 24 s longer each. If that delay matters during planned drains, tell me and we can look at it.
- Six attempts means roughly 50% more POSTs to a gateway that is already struggling.
- No one gave a reason for the value six beyond the blip problem in your request, so I recorded only the new value. If there is a measured blip length behind it, tell me and I can note it beside `MAX_ATTEMPTS`.
