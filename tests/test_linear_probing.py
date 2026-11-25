import unittest

from src.linear_probing import LinearProbingHashTable


class LinearProbingHashTableTest(unittest.TestCase):
    def test_horner_hash_and_trace(self):
        table = LinearProbingHashTable()

        self.assertEqual(table.hash_index("abc"), 2)
        self.assertEqual(
            table.hash_trace("abc"),
            (("a", 1), ("b", 1), ("c", 2)),
        )
        self.assertEqual(table.hash_index(""), 0)
        self.assertEqual(table.hash_trace(""), ())

    def test_insert_and_get_value(self):
        table = LinearProbingHashTable()

        table.put("key", "value")

        self.assertEqual(table.get("key"), "value")
        self.assertEqual(table.size, 1)
        self.assertEqual(table.capacity, 8)

    def test_colliding_keys_probe_next_buckets(self):
        table = LinearProbingHashTable(max_load=None)
        self.assertEqual(table.hash_index("a"), table.hash_index("i"))

        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")
        self.assertEqual(table.probe_trace("i"), (1, 2))
        self.assertEqual(table.get_with_probes("i"), ("second", 2))
        self.assertEqual(table.size, 2)

    def test_probe_wraps_from_last_bucket_to_zero(self):
        table = LinearProbingHashTable(initial_capacity=4, max_load=None)
        self.assertEqual(table.hash_index("c"), 3)
        self.assertEqual(table.hash_index("g"), 3)

        table.put("c", "last")
        table.put("g", "wrapped")

        self.assertEqual(table.get("g"), "wrapped")
        self.assertEqual(table.probe_trace("g"), (3, 0))
        self.assertEqual(table.get_with_probes("g"), ("wrapped", 2))

    def test_full_table_search_terminates_and_new_insert_raises(self):
        table = LinearProbingHashTable(initial_capacity=3, max_load=None)
        entries = (("a", "one"), ("b", "two"), ("c", "three"))
        for key, value in entries:
            table.put(key, value)

        self.assertEqual(table.size, table.capacity)
        initial_index = table.hash_index("missing")
        full_probe_path = tuple(
            (initial_index + offset) % table.capacity
            for offset in range(table.capacity)
        )
        self.assertEqual(table.probe_trace("missing"), full_probe_path)
        self.assertEqual(table.get_with_probes("missing"), (None, 3))
        with self.assertRaises(OverflowError):
            table.put("extra", "four")
        self.assertEqual(table.size, 3)

    def test_existing_key_can_be_updated_when_table_is_full(self):
        table = LinearProbingHashTable(initial_capacity=2, max_load=None)
        table.put("a", "old")
        table.put("b", "other")

        table.put("a", "new")

        self.assertEqual(table.get("a"), "new")
        self.assertEqual(table.size, 2)

    def test_missing_key_stops_at_first_empty_bucket(self):
        table = LinearProbingHashTable(max_load=None)

        self.assertEqual(table.get("missing"), None)
        self.assertEqual(table.get_with_probes("missing"), (None, 1))
        self.assertEqual(table.probe_trace("missing"), (table.hash_index("missing"),))

    def test_updates_existing_key_without_increasing_size(self):
        table = LinearProbingHashTable(max_load=None)
        table.put("a", "old")
        table.put("i", "other")

        table.put("a", "new")

        self.assertEqual(table.get("a"), "new")
        self.assertEqual(table.get("i"), "other")
        self.assertEqual(table.size, 2)

    def test_load_factor_boundary_and_growth(self):
        table = LinearProbingHashTable()
        for index in range(6):
            table.put(f"key-{index}", str(index))

        self.assertEqual(table.capacity, 8)
        self.assertEqual(table.load_factor, 0.75)

        table.put("key-6", "6")

        self.assertGreaterEqual(table.capacity, 16)
        self.assertLessEqual(table.load_factor, 0.75)

    def test_resize_rehashes_and_preserves_all_entries(self):
        table = LinearProbingHashTable()
        entries = tuple((f"key-{index}", f"value-{index}") for index in range(7))
        for key, value in entries:
            table.put(key, value)

        self.assertGreater(table.capacity, 8)
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_none_max_load_disables_automatic_growth_until_full(self):
        table = LinearProbingHashTable(initial_capacity=4, max_load=None)
        entries = (("a", "one"), ("b", "two"), ("c", "three"), ("d", "four"))
        for key, value in entries:
            table.put(key, value)

        self.assertEqual(table.capacity, 4)
        for key, value in entries:
            with self.subTest(key=key):
                self.assertEqual(table.get(key), value)

    def test_invalid_capacity_and_max_load_are_rejected(self):
        for capacity in (0, -1, 1.5, True):
            with self.subTest(capacity=capacity):
                with self.assertRaises(ValueError):
                    LinearProbingHashTable(initial_capacity=capacity)

        for max_load in (0, -0.1, float("inf"), float("nan")):
            with self.subTest(max_load=max_load):
                with self.assertRaises(ValueError):
                    LinearProbingHashTable(max_load=max_load)


if __name__ == "__main__":
    unittest.main()
