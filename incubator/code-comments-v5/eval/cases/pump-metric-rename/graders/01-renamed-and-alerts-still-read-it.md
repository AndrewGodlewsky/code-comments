---
type: llm
focus: core
weight: 2
---

Hidden tests: after two starts at a station the exporter serves pump_starts_total for it with the value 2, and the StationPumpsIdle and PumpShortCycling rules in deploy/alert_rules.yml each read a counter the exporter serves with that value, directly or through a recording rule that only renames it, their expressions otherwise unchanged.
