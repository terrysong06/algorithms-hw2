import unittest

from src.hash_table import ChainedHashTable


class ChainedHashTableTest(unittest.TestCase):
    def test_horner_hash_and_trace(self):
        table = ChainedHashTable()

        self.assertEqual(table.hash_index("abc"), 2)
        self.assertEqual(
            table.hash_trace("abc"),
            (("a", 1), ("b", 1), ("c", 2)),
        )
        self.assertEqual(table.hash_index(""), 0)
        self.assertEqual(table.hash_trace(""), ())

    def test_initial_capacity_and_load_factor(self):
        table = ChainedHashTable()

        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.size, 0)
        self.assertEqual(table.load_factor, 0)

        table.put("one", "1")
        self.assertEqual(table.size, 1)
        self.assertEqual(table.load_factor, 1 / 8)

    def test_colliding_keys_are_both_retrievable(self):
        table = ChainedHashTable()
        self.assertEqual(table.hash_index("a"), table.hash_index("i"))

        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(table.size, 2)

    def test_put_updates_existing_key_without_increasing_size(self):
        table = ChainedHashTable()
        table.put("key", "old")
        table.put("key", "new")

        self.assertEqual(table.get("key"), "new")
        self.assertEqual(table.size, 1)

    def test_missing_key_returns_none(self):
        table = ChainedHashTable()

        self.assertIsNone(table.get("missing"))

    def test_successful_and_failed_search_costs_count_compared_nodes(self):
        table = ChainedHashTable()
        table.put("a", "first")
        table.put("i", "second")

        value, probes = table.get_with_probes("i")
        self.assertEqual(value, "second")
        self.assertEqual(probes, 1)

        value, probes = table.get_with_probes("a")
        self.assertEqual(value, "first")
        self.assertEqual(probes, 2)

        value, probes = table.get_with_probes("q")
        self.assertIsNone(value)
        self.assertEqual(probes, 2)

    def test_search_in_empty_bucket_costs_zero(self):
        table = ChainedHashTable()

        self.assertEqual(table.get_with_probes("a"), (None, 0))

    def test_load_factor_boundary_and_growth(self):
        table = ChainedHashTable()
        for index in range(6):
            table.put(f"key-{index}", str(index))

        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.load_factor, 0.75)

        table.put("key-6", "6")

        self.assertGreaterEqual(table.capacity, 16)
        self.assertLessEqual(table.load_factor, 0.75)

    def test_resize_rehashes_and_preserves_all_entries(self):
        table = ChainedHashTable()
        entries = tuple((f"key-{index}", f"value-{index}") for index in range(7))
        for key, value in entries:
            table.put(key, value)

        self.assertGreater(table.capacity, 8)
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_none_max_load_disables_automatic_growth(self):
        table = ChainedHashTable(max_load=None)
        entries = tuple((f"key-{index}", f"value-{index}") for index in range(20))
        for key, value in entries:
            table.put(key, value)

        self.assertEqual(table.capacity, 8)
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_invalid_initial_capacity_raises_value_error(self):
        for capacity in (0, -1, 1.5, True):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    ChainedHashTable(initial_capacity=capacity)

    def test_invalid_max_load_raises_value_error(self):
        for max_load in (0, -0.1, float("inf"), float("nan")):
            with self.subTest(max_load=max_load):
                with self.assertRaises(ValueError):
                    ChainedHashTable(max_load=max_load)


if __name__ == "__main__":
    unittest.main()
