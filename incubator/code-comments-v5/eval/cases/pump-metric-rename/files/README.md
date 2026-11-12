# pumpwatch

Telemetry for the water board's sewage pumping stations. `pumps/` reads the event
feed from the station controllers and serves Prometheus metrics on port 9410.
`deploy/` holds the Prometheus scrape config and its alert rules.

Run the tests with `python -m unittest`.
