from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from cyengine.native_engine import Hexchess as CyHexchess
from cyengine.native_engine import search as cy_search
from pyengine.benchmark import DEFAULT_BENCHMARK_FILE, format_top_moves, load_benchmarks, median_ms
from pyengine.native_engine import Hexchess as PyHexchess
from pyengine.native_engine import search as py_search


EngineFactory = Callable[[str], Any]
EngineSearch = Callable[[Any, int], dict[str, Any]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run side-by-side pyengine and cyengine benchmarks.')
    parser.add_argument('--file', type=Path, default=DEFAULT_BENCHMARK_FILE, help='Benchmark YAML file')
    parser.add_argument('--depths', type=int, nargs='+', default=[3, 4], help='Depths to benchmark')
    parser.add_argument('--repeat', type=int, default=3, help='Runs per benchmark/depth')
    parser.add_argument('--filter', dest='name_filter', default='', help='Only run benchmark names containing this text')
    parser.add_argument('--top', type=int, default=3, help='How many top moves to display')
    return parser.parse_args()


def create_position(case: Any, engine_name: str) -> Any:
    engine_type: EngineFactory = CyHexchess if engine_name == 'cyengine' else PyHexchess

    if case.fen:
        return engine_type.parse(case.fen)

    if case.sequence is not None:
        return engine_type.init().apply(case.sequence)

    raise ValueError(f'Benchmark {case.name} does not define fen or sequence')


def run_engine_case(case: Any, depth: int, repeat: int, engine_name: str) -> dict[str, Any]:
    durations: list[float] = []
    evaluations: list[int] = []
    result: dict[str, Any] | None = None
    search_fn: EngineSearch = cy_search if engine_name == 'cyengine' else py_search

    for _ in range(repeat):
        position = create_position(case, engine_name)
        started_at = time.perf_counter()
        result = search_fn(position, depth)
        durations.append(time.perf_counter() - started_at)
        evaluations.append(int(result['evaluations']))

    assert result is not None
    elapsed_ms = median_ms(durations)
    median_evaluations = sorted(evaluations)[len(evaluations) // 2]
    evals_per_ms = median_evaluations / elapsed_ms if elapsed_ms > 0 else 0.0

    return {
        'engine': engine_name,
        'median_ms': elapsed_ms,
        'evaluations': median_evaluations,
        'evals_per_ms': evals_per_ms,
        'result': result,
    }


def format_ratio(numerator: float, denominator: float) -> str:
    if denominator == 0:
        return 'n/a'
    return f'{numerator / denominator:.2f}x'


def main() -> int:
    args = parse_args()
    cases = load_benchmarks(args.file)

    if args.name_filter:
        needle = args.name_filter.lower()
        cases = [case for case in cases if needle in case.name.lower()]

    if not cases:
        print('No benchmark cases selected.')
        return 1

    print(f'Benchmark file: {args.file}')
    print(f'Cases: {len(cases)} | Depths: {", ".join(str(depth) for depth in args.depths)} | Repeat: {args.repeat}')
    print()

    for case in cases:
        print(f'[{case.category}] {case.name}')
        if case.notes:
            print(f'  notes: {case.notes}')

        for depth in args.depths:
            py_summary = run_engine_case(case, depth, args.repeat, 'pyengine')
            cy_summary = run_engine_case(case, depth, args.repeat, 'cyengine')
            speedup = format_ratio(py_summary['median_ms'], cy_summary['median_ms'])
            throughput = format_ratio(cy_summary['evals_per_ms'], py_summary['evals_per_ms'])

            print(f'  depth {depth}:')
            print(
                f'    pyengine: {py_summary["median_ms"]:.1f} ms | '
                f'{py_summary["evaluations"]:,} evals | '
                f'{py_summary["evals_per_ms"]:.2f} evals/ms | '
                f'top {args.top}: {format_top_moves(py_summary["result"], args.top)}'
            )
            print(
                f'    cyengine: {cy_summary["median_ms"]:.1f} ms | '
                f'{cy_summary["evaluations"]:,} evals | '
                f'{cy_summary["evals_per_ms"]:.2f} evals/ms | '
                f'top {args.top}: {format_top_moves(cy_summary["result"], args.top)}'
            )
            print(f'    ratio: {speedup} faster by time | {throughput} eval throughput')

        print()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())