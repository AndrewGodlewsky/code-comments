# accounts-service

Account lifecycle for the subscription product.

- `accounts/events.py`: helpers over the login event stream.
- `accounts/sessions.py`: login counts.
- `accounts/devices.py`: each user's most recent device.
- `accounts/export.py`: the nightly table export.
- `reports/weekly.py`: the weekly users report.
- `billing/`: the billing team's SQL.
- `docs/trial.md`: how the free trial works.
