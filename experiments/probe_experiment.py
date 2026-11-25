import csv
import math
import random
import sys
from pathlib import Path
from typing import NamedTuple, Sequence

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.hash_table import ChainedHashTable


SEED = 42
BUCKET_COUNT = 1000
QUERY_COUNT = 10000
RESULTS_CSV = Path("experiments/results.csv")
RESULTS_SVG = Path("experiments/probe_costs.svg")


class ExperimentResult(NamedTuple):
    load_factor: float
    seed: int
    bucket_count: int
    max_load: float | None
    item_count: int
    successful_query_count: int
    failed_query_count: int
    measured_success_probes: float
    theoretical_success_probes: float
    success_abs_error: float
    measured_failure_probes: float
    theoretical_failure_probes: float
    failure_abs_error: float


def load_factors() -> tuple[float, ...]:
    return tuple(step / 4 for step in range(1, 17))


def measure_search_costs(
    table: ChainedHashTable[str],
    successful_keys: Sequence[str],
    missing_keys: Sequence[str],
) -> tuple[float, float]:
    if not successful_keys:
        raise ValueError("successful_keys must not be empty")
    if not missing_keys:
        raise ValueError("missing_keys must not be empty")

    successful_probes = sum(
        table.get_with_probes(key)[1] for key in successful_keys
    )
    failed_probes = sum(table.get_with_probes(key)[1] for key in missing_keys)
    return (
        successful_probes / len(successful_keys),
        failed_probes / len(missing_keys),
    )


def theoretical_costs(alpha: float) -> tuple[float, float]:
    return 1 + alpha / 2, alpha


def _random_key(generator: random.Random, prefix: str) -> str:
    return f"{prefix}-{generator.getrandbits(128):032x}"


def _build_experiment_keys(
    table: ChainedHashTable[str],
    item_count: int,
    generator: random.Random,
) -> tuple[list[str], list[str]]:
    successful_keys = []
    while len(successful_keys) < item_count:
        key = _random_key(generator, "stored")
        if table.get(key) is None:
            table.put(key, key)
            successful_keys.append(key)

    missing_table: ChainedHashTable[str] = ChainedHashTable(
        initial_capacity=BUCKET_COUNT,
        max_load=None,
    )
    missing_keys = []
    while len(missing_keys) < QUERY_COUNT:
        key = _random_key(generator, "missing")
        if table.get(key) is None and missing_table.get(key) is None:
            missing_table.put(key, key)
            missing_keys.append(key)
    return successful_keys, missing_keys


def _run_load_factor(
    alpha: float,
    generator: random.Random,
) -> ExperimentResult:
    item_count = int(alpha * BUCKET_COUNT)
    table: ChainedHashTable[str] = ChainedHashTable(
        initial_capacity=BUCKET_COUNT,
        max_load=None,
    )
    stored_keys, missing_keys = _build_experiment_keys(table, item_count, generator)
    successful_queries = [
        generator.choice(stored_keys) for _ in range(QUERY_COUNT)
    ]

    measured_success, measured_failure = measure_search_costs(
        table,
        successful_queries,
        missing_keys,
    )
    theoretical_success, theoretical_failure = theoretical_costs(alpha)
    return ExperimentResult(
        load_factor=alpha,
        seed=SEED,
        bucket_count=table.capacity,
        max_load=None,
        item_count=table.size,
        successful_query_count=len(successful_queries),
        failed_query_count=len(missing_keys),
        measured_success_probes=measured_success,
        theoretical_success_probes=theoretical_success,
        success_abs_error=abs(measured_success - theoretical_success),
        measured_failure_probes=measured_failure,
        theoretical_failure_probes=theoretical_failure,
        failure_abs_error=abs(measured_failure - theoretical_failure),
    )


def write_results_csv(
    rows: Sequence[ExperimentResult],
    path: str | Path = RESULTS_CSV,
) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(ExperimentResult._fields)
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
    rows: Sequence[ExperimentResult],
    path: str | Path = RESULTS_SVG,
) -> None:
    if not rows:
        raise ValueError("rows must not be empty")

    width = 1000
    height = 600
    plot_left = 90
    plot_right = 700
    plot_top = 80
    plot_bottom = 490
    max_value = max(
        max(
            row.measured_success_probes,
            row.theoretical_success_probes,
            row.measured_failure_probes,
            row.theoretical_failure_probes,
        )
        for row in rows
    )
    y_max = max(1, math.ceil(max_value * 1.1))

    def x_position(alpha: float) -> float:
        return plot_left + (alpha - 0.25) / (4.0 - 0.25) * (
            plot_right - plot_left
        )

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
            "Chained Hash Table Search Cost vs Load Factor",
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

    x_ticks = tuple(step / 4 for step in range(1, 17))
    for alpha in x_ticks:
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
                "Average node comparisons</text>"
            ),
        )
    )

    series = (
        (
            "Successful search probes (measured)",
            "measured_success_probes",
            "#1f77b4",
            "solid",
        ),
        (
            "Successful search probes (theoretical)",
            "theoretical_success_probes",
            "#1f77b4",
            "dashed",
        ),
        (
            "Failed search probes (measured)",
            "measured_failure_probes",
            "#d62728",
            "solid",
        ),
        (
            "Failed search probes (theoretical)",
            "theoretical_failure_probes",
            "#d62728",
            "dashed",
        ),
    )
    for label, field, color, line_style in series:
        points = " ".join(
            f"{x_position(row.load_factor):.1f},"
            f"{y_position(getattr(row, field)):.1f}"
            for row in rows
        )
        dash = ' stroke-dasharray="6,4"' if line_style == "dashed" else ""
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

    legend_x = 730
    legend_y = 150
    for index, (label, _, color, line_style) in enumerate(series):
        y = legend_y + index * 34
        dash = ' stroke-dasharray="6,4"' if line_style == "dashed" else ""
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
) -> tuple[ExperimentResult, ...]:
    generator = random.Random(SEED)
    rows = tuple(_run_load_factor(alpha, generator) for alpha in load_factors())
    write_results_csv(rows, csv_path)
    write_results_svg(rows, svg_path)
    return rows


def main() -> None:
    rows = run_experiment()
    print("\t".join(ExperimentResult._fields))
    for row in rows:
        print(
            "\t".join(
                f"{value:.6f}" if isinstance(value, float) else str(value)
                for value in row
            )
        )


if __name__ == "__main__":
    main()
