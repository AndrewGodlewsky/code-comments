The counter is now served as pump_starts_total, so the Grafana board has data again.

One more file used the old name: deploy/alert_rules.yml. Its StationPumpsIdle and
PumpShortCycling rules read the counter, and the comment at the top of that file says
Prometheus treats an unknown name as an empty series that never fires. Renaming only the
exporter would have stopped both pages without any error. I changed the two expressions
to pump_starts_total in the same change and left the rest of the rules as they were.

I also added a one-line note above the name in pumps/metrics.py saying the alert rules
read it. The tests pass.
