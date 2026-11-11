"""Drain the outbox through send_alert, one alert at a time.

Alerts go out in the order they were raised. In a full outage each one holds the worker
until send_alert drops it, so a backlog of 40 alerts takes about 21 minutes to clear.
"""

import time

from alerts.sender import send_alert


def drain(outbox, gateway, sleep=time.sleep):
    """Send every alert in `outbox`, oldest first, and return how many the gateway took."""
    delivered = 0
    for alert in outbox:
        delivered += send_alert(gateway, alert, sleep=sleep)
    return delivered
