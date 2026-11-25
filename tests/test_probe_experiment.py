import tempfile
import unittest
from pathlib import Path

from src.hash_table import ChainedHashTable
from experiments.probe_experiment import (
    load_factors,
    measure_search_costs,
    run_experiment,
    theoretical_costs,
)


class ProbeExperimentTest(unittest.TestCase):
    def test_load_factors_cover_requested_range(self):
        self.assertEqual(
            load_factors(),
            tuple(step / 4 for step in range(1, 17)),
        )

    def test_measure_search_costs_uses_actual_node_comparisons(self):
        table = ChainedHashTable(initial_capacity=8, max_load=None)
        table.put("a", "value-a")
        table.put("i", "value-i")

        successful_cost, failed_cost = measure_search_costs(
            table,
            ("a", "i"),
            ("z",),
        )

        self.assertEqual(successful_cost, 1.5)
        self.assertEqual(failed_cost, 0.0)

    def test_measure_search_costs_rejects_empty_query_groups(self):
        table = ChainedHashTable(max_load=None)

        with self.assertRaises(ValueError):
            measure_search_costs(table, (), ("missing",))
        with self.assertRaises(ValueError):
            measure_search_costs(table, ("present",), ())

    def test_theoretical_costs_follow_chaining_formulas(self):
        self.assertEqual(theoretical_costs(0.25), (1.125, 0.25))
        self.assertEqual(theoretical_costs(4.0), (3.0, 4.0))

    def test_run_experiment_writes_all_configured_results(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "results.csv"
            svg_path = Path(directory) / "costs.svg"

            rows = run_experiment(csv_path=csv_path, svg_path=svg_path)

            self.assertEqual(len(rows), 16)
            self.assertTrue(csv_path.is_file())
            self.assertTrue(svg_path.is_file())
            for row, alpha in zip(rows, load_factors()):
                with self.subTest(alpha=alpha):
                    self.assertEqual(row.load_factor, alpha)
                    self.assertEqual(row.seed, 42)
                    self.assertEqual(row.bucket_count, 1000)
                    self.assertEqual(row.item_count, int(alpha * 1000))
                    self.assertIsNone(row.max_load)
                    self.assertEqual(row.successful_query_count, 10000)
                    self.assertEqual(row.failed_query_count, 10000)
            csv_lines = csv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(csv_lines), 17)
            self.assertIn("success_abs_error", csv_lines[0])
            self.assertIn("failure_abs_error", csv_lines[0])
            svg = svg_path.read_text(encoding="utf-8")
            self.assertIn("Chained Hash Table Search Cost vs Load Factor", svg)
            self.assertIn("Load factor (alpha)", svg)
            self.assertIn("Average node comparisons", svg)
            self.assertIn("Successful search probes", svg)
            self.assertIn("Failed search probes", svg)
            self.assertIn("Successful search probes (theoretical)", svg)
            self.assertIn("Failed search probes (theoretical)", svg)


if __name__ == "__main__":
    unittest.main()
