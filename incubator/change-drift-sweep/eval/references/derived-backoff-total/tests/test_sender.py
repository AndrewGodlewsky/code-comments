import unittest

from alerts.config import BASE_DELAY_S, MAX_ATTEMPTS
from alerts.sender import GatewayError, send_alert
from alerts.worker import drain


class Gateway:
    def __init__(self, status=None):
        self.status = status
        self.posts = 0

    def post(self, alert):
        self.posts += 1
        if self.status is not None:
            raise GatewayError(self.status)


class SendAlertTest(unittest.TestCase):
    def test_delivers(self):
        self.assertTrue(send_alert(Gateway(), {"id": 1}, sleep=lambda s: None))

    def test_gives_up_after_max_attempts(self):
        gateway, waits = Gateway(status=503), []
        with self.assertLogs("alerts.sender", "WARNING"):
            self.assertFalse(send_alert(gateway, {"id": 1}, sleep=waits.append))
        self.assertEqual(gateway.posts, MAX_ATTEMPTS)
        self.assertEqual(waits, [BASE_DELAY_S * 2 ** i for i in range(MAX_ATTEMPTS - 1)])

    def test_client_error_is_not_retried(self):
        gateway = Gateway(status=400)
        with self.assertLogs("alerts.sender", "WARNING"):
            self.assertFalse(send_alert(gateway, {"id": 1}, sleep=lambda s: None))
        self.assertEqual(gateway.posts, 1)


class DrainTest(unittest.TestCase):
    def test_counts_delivered_alerts(self):
        self.assertEqual(drain([{"id": 1}, {"id": 2}], Gateway(), sleep=lambda s: None), 2)

    def test_outage_tries_every_alert_in_full(self):
        gateway = Gateway(status=503)
        with self.assertLogs("alerts.sender", "WARNING"):
            self.assertEqual(drain([{"id": 1}, {"id": 2}], gateway, sleep=lambda s: None), 0)
        self.assertEqual(gateway.posts, 2 * MAX_ATTEMPTS)


if __name__ == "__main__":
    unittest.main()
