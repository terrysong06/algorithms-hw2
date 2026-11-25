import csv
import math
import random
import sys
from pathlib import Path
from typing import NamedTuple, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hash_table import ChainedHashTable
from src.linear_probing import LinearProbingHashTable


SEED = 42
BUCKET_COUNT = 4093
QUERY_COUNT = 10000
LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
RESULTS_CSV = Path("experiments/comparison_results.csv")
RESULTS_SVG = Path("experiments/comparison.svg")


class ComparisonResult(NamedTuple):
    load_factor: float
    seed: int
    bucket_count: int
    max_load: None
    item_count: int
    successful_query_count: int
    failed_query_count: int
    chaining_measured_success: float
    chaining_theoretical_success: float
    chaining_measured_failure: float
    chaining_theoretical_failure: float
    linear_measured_success: float
    linear_theoretical_success: float
    linear_measured_failure: float
    linear_theoretical_failure: float


def load_factors() -> tuple[float, ...]:
    return LOAD_FACTORS


def measure_search_costs(
    chained: ChainedHashTable[str],
    linear: LinearProbingHashTable[str],
    successful_keys: Sequence[str],
    missing_keys: Sequence[str],
) -> tuple[float, float, float, float]:
    if not successful_keys:
        raise ValueError("successful_keys must not be empty")
    if not missing_keys:
        raise ValueError("missing_keys must not be empty")

    chaining_success_probes = 0
    linear_success_probes = 0
    for key in successful_keys:
        chained_value, chained_probes = chained.get_with_probes(key)
        linear_value, linear_probes = linear.get_with_probes(key)
        if chained_value is None or linear_value is None:
            raise RuntimeError(f"successful search key was not found: {key}")
        chaining_success_probes += chained_probes
        linear_success_probes += linear_probes

    chaining_failure_probes = 0
    linear_failure_probes = 0
    for key in missing_keys:
        chained_value, chained_probes = chained.get_with_probes(key)
        linear_value, linear_probes = linear.get_with_probes(key)
        if chained_value is not None or linear_value is not None:
            raise RuntimeError(f"missing search key was unexpectedly found: {key}")
        chaining_failure_probes += chained_probes
        linear_failure_probes += linear_probes

    return (
        chaining_success_probes / len(successful_keys),
        chaining_failure_probes / len(missing_keys),
        linear_success_probes / len(successful_keys),
        linear_failure_probes / len(missing_keys),
    )


def theoretical_costs(
    alpha: float,
) -> tuple[float, float, float, float]:
    return (
        1 + alpha / 2,
        alpha,
        (1 + 1 / (1 - alpha)) / 2,
        (1 + 1 / (1 - alpha) ** 2) / 2,
    )


def _random_url(generator: random.Random, index: int) -> str:
    return (
        "https://example.com/stored/"
        f"{generator.getrandbits(128):032x}/{index}"
    )


def _run_load_factor(
    alpha: float,
    generator: random.Random,
) -> ComparisonResult:
    item_count = int(alpha * BUCKET_COUNT)
    successful_stored_keys = [
        _random_url(generator, index) for index in range(item_count)
    ]
    successful_queries = tuple(
        generator.choice(successful_stored_keys)
        for _ in range(QUERY_COUNT)
    )
    missing_queries = tuple(
        "https://missing.example/"
        f"{generator.getrandbits(128):032x}/{index}"
        for index in range(QUERY_COUNT)
    )

    chained: ChainedHashTable[str] = ChainedHashTable(
        initial_capacity=BUCKET_COUNT,
        max_load=None,
    )
    linear: LinearProbingHashTable[str] = LinearProbingHashTable(
        initial_capacity=BUCKET_COUNT,
        max_load=None,
    )
    for key in successful_stored_keys:
        chained.put(key, key)
        linear.put(key, key)

    (
        chaining_measured_success,
        chaining_measured_failure,
        linear_measured_success,
        linear_measured_failure,
    ) = measure_search_costs(
        chained,
        linear,
        successful_queries,
        missing_queries,
    )
    (
        chaining_theoretical_success,
        chaining_theoretical_failure,
        linear_theoretical_success,
        linear_theoretical_failure,
    ) = theoretical_costs(alpha)
    return ComparisonResult(
        load_factor=alpha,
        seed=SEED,
        bucket_count=BUCKET_COUNT,
        max_load=None,
        item_count=item_count,
        successful_query_count=len(successful_queries),
        failed_query_count=len(missing_queries),
        chaining_measured_success=chaining_measured_success,
        chaining_theoretical_success=chaining_theoretical_success,
        chaining_measured_failure=chaining_measured_failure,
        chaining_theoretical_failure=chaining_theoretical_failure,
        linear_measured_success=linear_measured_success,
        linear_theoretical_success=linear_theoretical_success,
        linear_measured_failure=linear_measured_failure,
        linear_theoretical_failure=linear_theoretical_failure,
    )


def write_results_csv(
    rows: Sequence[ComparisonResult],
    path: str | Path = RESULTS_CSV,
) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(ComparisonResult._fields)
        for row in rows:
            writer.writerow(
                tuple("None" if value is None else value for value in row)
            )


def _svg_text(
    x: float,
    y: float,
    text: str,
    font_size: int,
    text_anchor: str | None = None,
    font_weight: str | None = None,
) -> str:
    attributes = [f'font-size="{font_size}"']
    if text_anchor is not None:
        attributes.append(f'text-anchor="{text_anchor}"')
    if font_weight is not None:
        attributes.append(f'font-weight="{font_weight}"')
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" {" ".join(attributes)}>'
        f"{text}</text>"
    )


def write_results_svg(
    rows: Sequence[ComparisonResult],
    path: str | Path = RESULTS_SVG,
) -> None:
    if not rows:
        raise ValueError("rows must not be empty")

    width = 1280
    height = 700
    plot_left = 90
    plot_right = 830
    plot_top = 80
    plot_bottom = 570
    max_value = max(
        max(
            row.chaining_measured_success,
            row.chaining_theoretical_success,
            row.chaining_measured_failure,
            row.chaining_theoretical_failure,
            row.linear_measured_success,
            row.linear_theoretical_success,
            row.linear_measured_failure,
            row.linear_theoretical_failure,
        )
        for row in rows
    )
    y_max = max(1, math.ceil(max_value * 1.1))

    def x_position(alpha: float) -> float:
        return plot_left + (alpha - 0.1) / 0.8 * (plot_right - plot_left)

    def y_position(value: float) -> float:
        return plot_bottom - value / y_max * (plot_bottom - plot_top)

    elements = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        _svg_text(
            width / 2,
            38,
            "Linear Probing and Chaining Search Costs",
            font_size=22,
            font_weight="bold",
            text_anchor="middle",
        ),
    ]

    for tick in range(y_max + 1):
        y = y_position(tick)
        elements.append(
            f'<line x1="{plot_left}" y1="{y:.1f}" x2="{plot_right}" '
            f'y2="{y:.1f}" stroke="#dddddd"/>'
        )
        elements.append(
            _svg_text(
                plot_left - 12,
                y + 5,
                str(tick),
                font_size=12,
                text_anchor="end",
            )
        )

    for alpha in LOAD_FACTORS:
        x = x_position(alpha)
        elements.append(
            f'<line x1="{x:.1f}" y1="{plot_top}" x2="{x:.1f}" '
            f'y2="{plot_bottom}" stroke="#eeeeee"/>'
        )
        elements.append(
            _svg_text(
                x,
                plot_bottom + 22,
                f"{alpha:g}",
                font_size=11,
                text_anchor="middle",
            )
        )

    elements.extend(
        (
            f'<line x1="{plot_left}" y1="{plot_top}" x2="{plot_left}" '
            f'y2="{plot_bottom}" stroke="#333333"/>',
            f'<line x1="{plot_left}" y1="{plot_bottom}" x2="{plot_right}" '
            f'y2="{plot_bottom}" stroke="#333333"/>',
            _svg_text(
                (plot_left + plot_right) / 2,
                height - 35,
                "Load factor (alpha)",
                font_size=15,
                text_anchor="middle",
            ),
            (
                f'<text x="25" y="{(plot_top + plot_bottom) / 2:.1f}" '
                'font-size="15" text-anchor="middle" '
                'transform="rotate(-90 25 '
                f'{(plot_top + plot_bottom) / 2:.1f})">'
                "Average probes</text>"
            ),
        )
    )

    series = (
        (
            "Chaining successful (measured)",
            "chaining_measured_success",
            "#1f77b4",
            False,
        ),
        (
            "Chaining successful (theoretical)",
            "chaining_theoretical_success",
            "#1f77b4",
            True,
        ),
        (
            "Chaining failed (measured)",
            "chaining_measured_failure",
            "#6baed6",
            False,
        ),
        (
            "Chaining failed (theoretical)",
            "chaining_theoretical_failure",
            "#6baed6",
            True,
        ),
        (
            "Linear probing successful (measured)",
            "linear_measured_success",
            "#d95f02",
            False,
        ),
        (
            "Linear probing successful (theoretical)",
            "linear_theoretical_success",
            "#d95f02",
            True,
        ),
        (
            "Linear probing failed (measured)",
            "linear_measured_failure",
            "#fdae6b",
            False,
        ),
        (
            "Linear probing failed (theoretical)",
            "linear_theoretical_failure",
            "#fdae6b",
            True,
        ),
    )
    for label, field, color, is_theoretical in series:
        points = " ".join(
            f"{x_position(row.load_factor):.1f},"
            f"{y_position(getattr(row, field)):.1f}"
            for row in rows
        )
        dash = ' stroke-dasharray="6,4"' if is_theoretical else ""
        elements.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" '
            f'stroke-width="2"{dash}/>'
        )
        for row in rows:
            x = x_position(row.load_factor)
            y = y_position(getattr(row, field))
            elements.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="{color}"/>'
            )

    legend_x = 865
    legend_y = 140
    for index, (label, _, color, is_theoretical) in enumerate(series):
        y = legend_y + index * 36
        dash = ' stroke-dasharray="6,4"' if is_theoretical else ""
        elements.append(
            f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" '
            f'stroke="{color}" stroke-width="2"{dash}/>'
        )
        elements.append(
            _svg_text(
                legend_x + 38,
                y + 5,
                label,
                font_size=12,
            )
        )

    elements.append("</svg>")
    Path(path).write_text("\n".join(elements), encoding="utf-8")


def run_experiment(
    csv_path: str | Path = RESULTS_CSV,
    svg_path: str | Path = RESULTS_SVG,
) -> tuple[ComparisonResult, ...]:
    generator = random.Random(SEED)
    rows = tuple(_run_load_factor(alpha, generator) for alpha in LOAD_FACTORS)
    write_results_csv(rows, csv_path)
    write_results_svg(rows, svg_path)
    return rows


def main() -> None:
    rows = run_experiment()
    print("\t".join(ComparisonResult._fields))
    for row in rows:
        print(
            "\t".join(
                f"{value:.6f}" if isinstance(value, float) else str(value)
                for value in row
            )
        )


if __name__ == "__main__":
    main()
