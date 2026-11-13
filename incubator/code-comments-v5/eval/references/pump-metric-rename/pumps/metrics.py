"""Prometheus metrics for the pumping stations.

StationMetrics keeps a starts counter and a wet-well level for each station, and
render() writes them in the text format that the exporter serves at /metrics.
"""

# deploy/alert_rules.yml reads this name; change the two together.
STARTS = "pump_starts_total"
LEVEL = "wet_well_level_metres"


class StationMetrics:
    def __init__(self):
        self.starts = {}
        self.levels = {}

    def pump_started(self, station):
        """Count one start of any pump at the station."""
        self.starts[station] = self.starts.get(station, 0) + 1

    def set_level(self, station, metres):
        self.levels[station] = metres

    def render(self):
        lines = [f"# HELP {STARTS} Times a pump at the station has switched on.",
                 f"# TYPE {STARTS} counter"]
        lines += [f'{STARTS}{{station="{name}"}} {count}' for name, count in sorted(self.starts.items())]
        lines += [f"# HELP {LEVEL} Wet-well depth above the sump floor, in metres.",
                  f"# TYPE {LEVEL} gauge"]
        lines += [f'{LEVEL}{{station="{name}"}} {depth}' for name, depth in sorted(self.levels.items())]
        return "\n".join(lines) + "\n"
