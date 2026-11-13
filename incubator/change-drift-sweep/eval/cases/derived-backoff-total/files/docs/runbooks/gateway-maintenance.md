# Runbook: planned gateway maintenance

1. Tell the on-call lead before the gateway starts draining.
2. While it drains, the gateway answers 503. The sender retries each alert three times, waiting longer each time, and then drops it.
3. After the drain, search the log for `alert_dropped` and raise again any alert that still matters.
