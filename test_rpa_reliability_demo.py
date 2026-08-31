import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from rpa_reliability_demo import MockPortal, SafetyStop, collect_one, run_batch


PROFILE = {"buyer_nickname": "buyer_demo", "purchase_count": 2, "cumulative_spend_cents": 10000, "average_order_value_cents": 5000, "note": ""}


class ReliableRpaDemoTests(unittest.TestCase):
    def test_inconsistent_double_read_stops_without_guessing(self):
        changed = dict(PROFILE, purchase_count=3)
        portal = MockPortal({"1001": ["buyer_demo"]}, {"buyer_demo": [PROFILE, changed]})
        with self.assertRaises(SafetyStop):
            collect_one("1001", portal)

    def test_grouped_order_is_queried_once_and_input_is_unchanged(self):
        rows = [
            {"main_order_id": "1001", "sku_id": "SKU-A"},
            {"main_order_id": "1001", "sku_id": "SKU-B"},
        ]
        original = deepcopy(rows)
        portal = MockPortal({"1001": ["buyer_demo"]}, {"buyer_demo": [PROFILE]})
        with tempfile.TemporaryDirectory() as directory:
            result = run_batch(rows, portal, Path(directory) / "result.json", Path(directory) / "history.sqlite3")
        self.assertEqual(rows, original)
        self.assertEqual(portal.search_count["1001"], 1)
        self.assertTrue(all(row["buyer_nickname"] == "buyer_demo" for row in result))

    def test_multiple_candidates_are_rejected(self):
        portal = MockPortal({"1001": ["buyer_a", "buyer_b"]}, {})
        with self.assertRaises(SafetyStop):
            collect_one("1001", portal)


if __name__ == "__main__":
    unittest.main()
