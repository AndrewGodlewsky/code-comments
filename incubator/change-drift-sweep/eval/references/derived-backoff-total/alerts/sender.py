"""Send on-call alerts to the paging gateway.

send_alert() makes at most six attempts, then drops the alert and logs it as
alert_dropped.
"""

import logging
import time

from alerts.config import BASE_DELAY_S, MAX_ATTEMPTS, RETRYABLE_STATUSES

log = logging.getLogger(__name__)


class GatewayError(Exception):
    """The gateway refused an alert with an HTTP status."""

    def __init__(self, status):
        super().__init__(f"gateway answered {status}")
        self.status = status


def send_alert(gateway, alert, sleep=time.sleep):
    """Deliver one alert. Return True if the gateway took it, False if it was dropped."""
    delay = BASE_DELAY_S
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            gateway.post(alert)
            return True
        except GatewayError as error:
            if error.status not in RETRYABLE_STATUSES or attempt == MAX_ATTEMPTS:
                break
        # Waits of 1, 2, 4, 8 and 16 s: the alert is dropped about 31 s after the first try.
        sleep(delay)
        delay *= 2
    log.warning("alert_dropped %s", alert)
    return False
