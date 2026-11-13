import unittest

from events.queue import consume


class ConsumeTest(unittest.TestCase):
    def test_posts_good_messages_and_returns_the_rest(self):
        posted = []
        failed = consume([{"kind": "refund", "amount": "2.00"}, {"kind": "mystery", "amount": "1.00"}],
                         posted.append, {"refund"})
        self.assertEqual(posted, [[("refunds", 200), ("cash", -200)]])
        self.assertEqual(failed, [{"kind": "mystery", "amount": "1.00"}])


if __name__ == "__main__":
    unittest.main()
