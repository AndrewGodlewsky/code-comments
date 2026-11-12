import re
import unittest
from pathlib import Path

from pumps.metrics import StationMetrics
from pumps.telemetry import apply_feed

ROOT = Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy"
SAMPLE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^}]*)\}\s+(\S+)\s*$")
# The two pump rules, with the metric name taken out: only the name may change.
PUMP_RULES = {"StationPumpsIdle": "increase(M[6h])==0", "PumpShortCycling": "increase(M[1h])>12"}


def served_after_two_starts():
    """{metric name: value} for the north station after two starts and one level reading."""
    metrics = StationMetrics()
    apply_feed(metrics, ["north START P1", "north START P2", "north LEVEL 1.20"])
    served = {}
    for line in metrics.render().splitlines():
        match = SAMPLE.match(line.strip())
        if match and 'station="north"' in match.group(2):
            served[match.group(1)] = float(match.group(3))
    return served


def rule_exprs():
    """({alert name: expr}, {recorded name: expr}) from every rule file under deploy/,
    read line by line. A block scalar (expr: | or expr: >) is joined into one line."""
    alerts, records, current = {}, {}, None
    for path in sorted(list(DEPLOY.rglob("*.yml")) + list(DEPLOY.rglob("*.yaml"))):
        lines = path.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i]
            i += 1
            line = raw.strip()
            if line.startswith("#"):
                continue
            named = re.match(r"-?\s*(alert|record):\s*(\S+)", line)
            if named:
                current = (named.group(1), named.group(2).strip("'\""))
                continue
            expr = re.match(r"-?\s*expr:\s*(.+)$", line)
            if not (expr and current):
                continue
            value = expr.group(1).strip()
            if re.fullmatch(r"[|>][+-]?", value):
                indent = len(raw) - len(raw.lstrip())
                parts = []
                while i < len(lines) and (not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > indent):
                    parts.append(lines[i].strip())
                    i += 1
                value = " ".join(p for p in parts if p)
            (alerts if current[0] == "alert" else records)[current[1]] = value.strip().strip("'\"")
    return alerts, records


def alert_exprs():
    return rule_exprs()[0]


def served_or_recorded(name, served, records):
    """The value a rule reading this name would see: the exporter's, or for a recording
    rule that only renames a served series (record: old, expr: new), that series'."""
    if name in served:
        return served[name]
    alias = re.fullmatch(r"\s*([a-zA-Z_:][a-zA-Z0-9_:]*)\s*(\{[^}]*\})?\s*", records.get(name, ""))
    return served.get(alias.group(1)) if alias else None


class StartsCounterTest(unittest.TestCase):
    def test_served_under_the_new_name(self):
        served = served_after_two_starts()
        self.assertEqual(served.get("pump_starts_total"), 2.0, served)

    def test_pump_alerts_read_a_served_counter(self):
        served = served_after_two_starts()
        exprs, records = rule_exprs()
        for alert, shape in PUMP_RULES.items():
            with self.subTest(alert=alert):
                self.assertIn(alert, exprs)
                names = re.findall(r"increase\(\s*([a-zA-Z_:][a-zA-Z0-9_:]*)\s*\[", exprs[alert])
                self.assertEqual(len(names), 1, exprs[alert])
                seen = served_or_recorded(names[0], served, records)
                self.assertEqual(seen, 2.0, f"{alert} reads {names[0]}, which the exporter serves, or a "
                                            f"recording rule gives, as {seen}")
                self.assertEqual(re.sub(r"\s+", "", exprs[alert].replace(names[0], "M")), shape)

    def test_level_alert_still_reads_the_gauge(self):
        exprs = alert_exprs()
        self.assertIn("WetWellHigh", exprs)
        self.assertIn("wet_well_level_metres", served_after_two_starts())
        self.assertEqual(re.sub(r"\s+", "", exprs["WetWellHigh"]), "max_over_time(wet_well_level_metres[5m])>2.5")


if __name__ == "__main__":
    unittest.main()
