import logging
import unittest

from alerts import config
from alerts.sender import GatewayError, send_alert

logging.disable(logging.CRITICAL)


class Down:
    def __init__(self):
        self.posts = 0

    def post(self, alert):
        self.posts += 1
        raise GatewayError(503)


class SixAttemptsTest(unittest.TestCase):
    def test_six_attempts_with_doubling_waits(self):
        gateway, waits = Down(), []
        self.assertFalse(send_alert(gateway, {"id": 1}, sleep=waits.append))
        self.assertEqual(gateway.posts, 6)
        self.assertEqual(waits, [1, 2, 4, 8, 16])

    def test_other_settings_unchanged(self):
        self.assertEqual(config.MAX_ATTEMPTS, 6)
        self.assertEqual(config.BASE_DELAY_S, 1)
        self.assertEqual(config.RETRYABLE_STATUSES, frozenset({502, 503, 504}))
        self.assertEqual(config.OUTBOX_RETENTION_DAYS, 7)

    def test_outage_drain_tries_each_alert_six_times(self):
        from alerts.worker import drain

        gateway, waits = Down(), []
        self.assertEqual(drain([{"id": 1}, {"id": 2}], gateway, sleep=waits.append), 0)
        self.assertEqual(gateway.posts, 12)
        self.assertEqual(sum(waits), 62)
