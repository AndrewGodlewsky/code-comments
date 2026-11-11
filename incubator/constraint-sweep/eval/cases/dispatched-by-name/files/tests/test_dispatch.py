import unittest

from events.dispatch import dispatch


class DispatchTest(unittest.TestCase):
    def test_hands_an_event_to_its_handler(self):
        self.assertEqual(dispatch({"kind": "refund", "amount": "1.00"}, {"refund"}),
                         [("refunds", 100), ("cash", -100)])

    def test_a_kind_that_is_not_on_is_an_error(self):
        with self.assertRaises(KeyError):
            dispatch({"kind": "mystery", "amount": "1.00"}, {"refund"})


if __name__ == "__main__":
    unittest.main()
