import unittest

from inventory.feed import latest_updates, total_units


def counts(updates):
    return {update["sku"]: update["count"] for update in latest_updates(updates)}


class LatestUpdatesTest(unittest.TestCase):
    def test_one_update_per_sku(self):
        updates = [{"sku": "A1", "count": 5}, {"sku": "B2", "count": 3}]
        self.assertEqual(len(latest_updates(updates)), 2)

    def test_later_update_wins(self):
        # The warehouse fixes a miscount by sending the SKU again further down the
        # same feed, so the count that arrives later is the true one.
        updates = [{"sku": "A1", "count": 5}, {"sku": "B2", "count": 3}, {"sku": "A1", "count": 4}]
        self.assertEqual(counts(updates), {"A1": 4, "B2": 3})

    def test_total_units(self):
        updates = [{"sku": "A1", "count": 5}, {"sku": "B2", "count": 3}, {"sku": "A1", "count": 4}]
        self.assertEqual(total_units(updates), 7)


if __name__ == "__main__":
    unittest.main()
