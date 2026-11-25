import math
import tempfile
import unittest
from pathlib import Path

from src.hash_table import ChainedHashTable
from src.linear_probing import LinearProbingHashTable
from experiments.compare_experiment import (
    BUCKET_COUNT,
    LOAD_FACTORS,
    QUERY_COUNT,
    SEED,
    load_factors,
    measure_search_costs,
    run_experiment,
    theoretical_costs,
)


class CompareExperimentTest(unittest.TestCase):
    def test_load_factors_and_fixed_settings(self):
        self.assertEqual(load_factors(), tuple(step / 10 for step in range(1, 10)))
        self.assertEqual(LOAD_FACTORS, load_factors())
        self.assertEqual(BUCKET_COUNT, 4093)
        self.assertEqual(SEED, 42)
        self.assertEqual(QUERY_COUNT, 10000)

    def test_measurement_counts_actual_nodes_and_slots(self):
        chained = ChainedHashTable(initial_capacity=8, max_load=None)
        linear = LinearProbingHashTable(initial_capacity=8, max_load=None)
        for key in ("a", "i"):
            chained.put(key, key)
            linear.put(key, key)

        measured = measure_search_costs(
            chained,
            linear,
            ("a", "i"),
            ("q",),
        )

        self.assertEqual(measured, (1.5, 2.0, 1.5, 3.0))

    def test_measurement_rejects_empty_query_groups(self):
        chained = ChainedHashTable(max_load=None)
        linear = LinearProbingHashTable(max_load=None)

        with self.assertRaises(ValueError):
            measure_search_costs(chained, linear, (), ("missing",))
        with self.assertRaises(ValueError):
            measure_search_costs(chained, linear, ("present",), ())

    def test_theoretical_costs_match_specified_formulas(self):
        alpha = 0.5
        chaining_success, chaining_failure, linear_success, linear_failure = (
            theoretical_costs(alpha)
        )

        self.assertAlmostEqual(chaining_success, 1 + alpha / 2)
        self.assertAlmostEqual(chaining_failure, alpha)
        self.assertAlmostEqual(linear_success, (1 + 1 / (1 - alpha)) / 2)
        self.assertAlmostEqual(
            linear_failure,
            (1 + 1 / (1 - alpha) ** 2) / 2,
        )

    def test_run_experiment_writes_all_comparison_results(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "comparison_results.csv"
            svg_path = Path(directory) / "comparison.svg"

            rows = run_experiment(csv_path=csv_path, svg_path=svg_path)

            self.assertEqual(len(rows), len(LOAD_FACTORS))
            self.assertTrue(csv_path.is_file())
            self.assertTrue(svg_path.is_file())
            for row, alpha in zip(rows, LOAD_FACTORS):
                with self.subTest(alpha=alpha):
                    self.assertEqual(row.load_factor, alpha)
                    self.assertEqual(row.seed, SEED)
                    self.assertEqual(row.bucket_count, BUCKET_COUNT)
                    self.assertEqual(row.item_count, int(alpha * BUCKET_COUNT))
                    self.assertIsNone(row.max_load)
                    self.assertEqual(row.successful_query_count, QUERY_COUNT)
                    self.assertEqual(row.failed_query_count, QUERY_COUNT)
                    self.assertTrue(
                        math.isfinite(row.chaining_measured_success)
                    )
                    self.assertTrue(math.isfinite(row.linear_measured_failure))

            csv_lines = csv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(csv_lines), len(LOAD_FACTORS) + 1)
            self.assertIn("chaining_measured_success", csv_lines[0])
            self.assertIn("linear_theoretical_failure", csv_lines[0])
            svg = svg_path.read_text(encoding="utf-8")
            self.assertIn("Linear Probing and Chaining Search Costs", svg)
            self.assertIn("Load factor (alpha)", svg)
            self.assertIn("Chaining successful (measured)", svg)
            self.assertIn("Linear probing failed (theoretical)", svg)


if __name__ == "__main__":
    unittest.main()
