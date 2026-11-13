# sensor-rollups

Turns raw sensor readings into hourly rollups and spike alerts.

- `metrics/readings.py`: parses a readings file (`load_readings`).
- `metrics/rollup.py`: hourly means per sensor.
- `alerts/spikes.py`: flags jumps between a sensor's consecutive readings.
- `cli/report.py`: prints the rollup and the spikes for one file.
- `cli/export.py`: dumps parsed readings as JSON lines for the dashboard.
