from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pyengine.native_engine import Hexchess, search


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_BENCHMARK_FILE = ROOT_DIR.parent / 'pyengine2' / 'benchmark' / 'benchmarks.yaml'


@dataclass(frozen=True, slots=True)
class BenchmarkCase:
    name: str
    category: str
    fen: str | None
    sequence: str | None
    notes: str

    def create_position(self) -> Hexchess:
        if self.fen:
            return Hexchess.parse(self.fen)

        if self.sequence is not None:
            return Hexchess.init().apply(self.sequence)

        raise ValueError(f'Benchmark {self.name} does not define fen or sequence')


def load_benchmarks(path: Path) -> list[BenchmarkCase]:
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))

    if not isinstance(raw, dict) or raw.get('version') != 1:
        raise ValueError(f'Unsupported benchmark file format: {path}')

    items = raw.get('benchmarks')
    if not isinstance(items, list):
        raise ValueError(f'Benchmark file has no benchmarks list: {path}')

    cases: list[BenchmarkCase] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('Invalid benchmark entry')

        name = item.get('name')
        category = item.get('category', 'uncategorized')
        fen = item.get('fen')
        sequence = item.get('sequence')
        notes = item.get('notes', '')

        if not isinstance(name, str) or not name:
            raise ValueError('Benchmark entry is missing a valid name')
        if fen is not None and not isinstance(fen, str):
            raise ValueError(f'Benchmark {name} has invalid fen')
        if sequence is not None and not isinstance(sequence, str):
            raise ValueError(f'Benchmark {name} has invalid sequence')
        if fen is None and sequence is None:
            raise ValueError(f'Benchmark {name} must define fen or sequence')

        cases.append(BenchmarkCase(name=name, category=str(category), fen=fen, sequence=sequence, notes=str(notes)))

    return cases


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run pyengine search benchmarks.')
    parser.add_argument('--file', type=Path, default=DEFAULT_BENCHMARK_FILE, help='Benchmark YAML file')
    parser.add_argument('--depths', type=int, nargs='+', default=[3, 4], help='Depths to benchmark')
    parser.add_argument('--repeat', type=int, default=3, help='Runs per benchmark/depth')
    parser.add_argument('--filter', dest='name_filter', default='', help='Only run benchmark names containing this text')
    parser.add_argument('--top', type=int, default=3, help='How many top moves to display')
    return parser.parse_args()


def median_ms(values: list[float]) -> float:
    return statistics.median(values) * 1000.0


def run_case(case: BenchmarkCase, depth: int, repeat: int) -> dict[str, Any]:
    durations: list[float] = []
    evaluations: list[int] = []
    result: dict[str, Any] | None = None

    for _ in range(repeat):
        position = case.create_position()
        started_at = time.perf_counter()
        result = search(position, depth)
        durations.append(time.perf_counter() - started_at)
        evaluations.append(int(result['evaluations']))

    assert result is not None
    elapsed_ms = median_ms(durations)
    median_evaluations = int(statistics.median(evaluations))
    evals_per_ms = median_evaluations / elapsed_ms if elapsed_ms > 0 else 0.0

    return {
        'name': case.name,
        'category': case.category,
        'depth': depth,
        'median_ms': elapsed_ms,
        'evaluations': median_evaluations,
        'evals_per_ms': evals_per_ms,
        'result': result,
        'notes': case.notes,
    }


def format_top_moves(result: dict[str, Any], top: int) -> str:
    sans = result.get('sans', [])
    if not isinstance(sans, list) or not sans:
        return '-'

    parts: list[str] = []
    for item in sans[:top]:
        if not isinstance(item, dict):
            continue
        san = item.get('san', '?')
        score = item.get('score', '?')
        if isinstance(score, float):
            parts.append(f'{san}:{score:.2f}')
        else:
            parts.append(f'{san}:{score}')

    return ', '.join(parts) if parts else '-'


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
            summary = run_case(case, depth, args.repeat)
            print(
                f'  depth {depth}: '
                f'{summary["median_ms"]:.1f} ms | '
                f'{summary["evaluations"]:,} evals | '
                f'{summary["evals_per_ms"]:.2f} evals/ms | '
                f'top {args.top}: {format_top_moves(summary["result"], args.top)}'
            )

        print()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())