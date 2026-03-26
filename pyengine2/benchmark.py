from __future__ import annotations

import argparse
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from pyengine2.native_engine import EvalOptions, Hexchess, San, static_eval_for_turn, search
from pyengine2.version import PYENGINE2_VERSION


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_BENCHMARK_FILE = ROOT_DIR / 'benchmark' / 'benchmarks.yaml'

STAGE1_BASELINE_SUITE = (
    {'mode': 'eval', 'filter': 'quiet-endgame-eval', 'repeat': 50},
    {'mode': 'moves', 'filter': 'slider-mobility-open', 'repeat': 10},
    {'mode': 'tactical-moves', 'filter': 'capture-storm-qsearch', 'repeat': 10},
    {'mode': 'search', 'filter': 'tt-transposition-midgame', 'depths': [4, 5], 'repeat': 3},
    {'mode': 'search', 'filter': 'capture-storm-qsearch', 'depths': [4, 5], 'repeat': 3},
    {'mode': 'search', 'filter': 'initial-position', 'depths': [4, 5], 'repeat': 3},
)


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
            position = Hexchess.init()
            for token in self.sequence.split():
                position.apply_move(San.parse(token))
            return position
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
    parser = argparse.ArgumentParser(description='Run pyengine2 search benchmarks.')
    parser.add_argument('--file', type=Path, default=DEFAULT_BENCHMARK_FILE, help='Benchmark YAML file')
    parser.add_argument('--output', type=Path, help='Optional YAML report output path')
    parser.add_argument('--suite', choices=('stage1-baseline',), help='Run a predefined benchmark suite')
    parser.add_argument(
        '--mode',
        choices=('search', 'moves', 'tactical-moves', 'eval'),
        default='search',
        help='Benchmark full search, full move generation, tactical-only move generation, or static evaluation',
    )
    parser.add_argument('--depths', type=int, nargs='+', default=[3, 4], help='Depths to benchmark')
    parser.add_argument('--repeat', type=int, default=3, help='Runs per benchmark/depth')
    parser.add_argument('--filter', dest='name_filter', default='', help='Only run benchmark names containing this text')
    parser.add_argument('--top', type=int, default=3, help='How many top moves to display')
    parser.add_argument('--diagnostics', action='store_true', help='Enable extra diagnostic search counters in benchmark reports')
    return parser.parse_args()


def median_ms(values: list[float]) -> float:
    return statistics.median(values) * 1000.0


def run_search_case(case: BenchmarkCase, depth: int, repeat: int, diagnostics: bool) -> dict[str, Any]:
    durations: list[float] = []
    evaluations: list[int] = []
    result: dict[str, Any] | None = None

    for _ in range(repeat):
        position = case.create_position()
        started_at = time.perf_counter()
        result = search(position, depth, diagnostics=diagnostics)
        durations.append(time.perf_counter() - started_at)
        evaluations.append(int(result['evaluations']))

    assert result is not None
    elapsed_ms = median_ms(durations)
    median_evaluations = int(statistics.median(evaluations))
    evals_per_ms = median_evaluations / elapsed_ms if elapsed_ms > 0 else 0.0

    return {
        'name': case.name,
        'category': case.category,
        'mode': 'search',
        'depth': depth,
        'median_ms': elapsed_ms,
        'units': median_evaluations,
        'units_label': 'evals',
        'units_per_ms': evals_per_ms,
        'result': result,
        'notes': case.notes,
    }


def run_movegen_case(case: BenchmarkCase, repeat: int, tactical_only: bool) -> dict[str, Any]:
    durations: list[float] = []
    generated_counts: list[int] = []
    last_moves: list[int] | None = None

    for _ in range(repeat):
        position = case.create_position()
        started_at = time.perf_counter()
        last_moves = position._current_moves_codes(tactical_only=tactical_only)
        durations.append(time.perf_counter() - started_at)
        generated_counts.append(len(last_moves))

    elapsed_ms = median_ms(durations)
    median_generated = int(statistics.median(generated_counts))
    moves_per_ms = median_generated / elapsed_ms if elapsed_ms > 0 else 0.0

    return {
        'name': case.name,
        'category': case.category,
        'mode': 'tactical-moves' if tactical_only else 'moves',
        'depth': None,
        'median_ms': elapsed_ms,
        'units': median_generated,
        'units_label': 'moves',
        'units_per_ms': moves_per_ms,
        'result': last_moves or [],
        'notes': case.notes,
    }


def run_eval_case(case: BenchmarkCase, repeat: int) -> dict[str, Any]:
    durations: list[float] = []
    scores: list[float] = []
    options = EvalOptions()

    for _ in range(repeat):
        position = case.create_position()
        started_at = time.perf_counter()
        score = static_eval_for_turn(position, options)
        durations.append(time.perf_counter() - started_at)
        scores.append(float(score))

    elapsed_ms = median_ms(durations)
    evals_per_ms = repeat / elapsed_ms if elapsed_ms > 0 else 0.0

    return {
        'name': case.name,
        'category': case.category,
        'mode': 'eval',
        'depth': None,
        'median_ms': elapsed_ms,
        'units': repeat,
        'units_label': 'evals',
        'units_per_ms': evals_per_ms,
        'result': statistics.median(scores),
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


def format_generated_moves(result: list[int], top: int) -> str:
    if not result:
        return '-'
    return ', '.join(str(San.from_code(move_code)) for move_code in result[:top])


def format_eval_result(result: float) -> str:
    return f'{result:.2f}'


def summary_report_data(summary: dict[str, Any], top: int) -> dict[str, Any]:
    report: dict[str, Any] = {
        'name': summary['name'],
        'category': summary['category'],
        'mode': summary['mode'],
        'medianMs': round(float(summary['median_ms']), 6),
        'units': int(summary['units']),
        'unitsLabel': summary['units_label'],
        'unitsPerMs': round(float(summary['units_per_ms']), 6),
    }
    if summary.get('notes'):
        report['notes'] = summary['notes']

    if summary['depth'] is not None:
        report['depth'] = int(summary['depth'])

    mode = summary['mode']
    if mode == 'search':
        result = summary['result']
        report['topMoves'] = result.get('sans', [])[:top]
        metrics = result.get('metrics')
        if isinstance(metrics, dict):
            report['metrics'] = metrics
    elif mode in {'moves', 'tactical-moves'}:
        report['sampleMoves'] = [str(San.from_code(move_code)) for move_code in summary['result'][:top]]
    else:
        report['staticEval'] = round(float(summary['result']), 6)

    return report


def write_yaml_report(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding='utf-8')


def print_search_summary(summary: dict[str, Any], top: int) -> None:
    print(
        f'  depth {summary["depth"]}: '
        f'{summary["median_ms"]:.1f} ms | '
        f'{summary["units"]:,} {summary["units_label"]} | '
        f'{summary["units_per_ms"]:.2f} {summary["units_label"]}/ms | '
        f'top {top}: {format_top_moves(summary["result"], top)}'
    )


def print_movegen_summary(summary: dict[str, Any], top: int) -> None:
    print(
        f'  {summary["median_ms"]:.3f} ms | '
        f'{summary["units"]:,} {summary["units_label"]} | '
        f'{summary["units_per_ms"]:.2f} {summary["units_label"]}/ms | '
        f'sample {top}: {format_generated_moves(summary["result"], top)}'
    )


def print_eval_summary(summary: dict[str, Any]) -> None:
    print(
        f'  {summary["median_ms"]:.6f} ms | '
        f'{summary["units"]:,} {summary["units_label"]} | '
        f'{summary["units_per_ms"]:.2f} {summary["units_label"]}/ms | '
        f'static eval: {format_eval_result(summary["result"])}'
    )


def run_suite(args: argparse.Namespace, cases: list[BenchmarkCase]) -> int:
    if args.suite != 'stage1-baseline':
        raise ValueError(f'Unsupported suite: {args.suite}')

    print(f'Benchmark file: {args.file}')
    print(f'Suite: {args.suite} | pyengine2 version: {PYENGINE2_VERSION}')
    print()

    suite_entries: list[dict[str, Any]] = []

    for entry in STAGE1_BASELINE_SUITE:
        mode = entry['mode']
        name_filter = str(entry['filter'])
        selected_cases = [case for case in cases if name_filter in case.name.lower()]
        if not selected_cases:
            print(f'No benchmark cases selected for suite entry: {name_filter}')
            return 1

        if mode == 'search':
            depths = entry['depths']
            repeat = int(entry['repeat'])
            print(f'Mode: {mode} | Filter: {name_filter} | Depths: {", ".join(str(depth) for depth in depths)} | Repeat: {repeat}')
        else:
            repeat = int(entry['repeat'])
            print(f'Mode: {mode} | Filter: {name_filter} | Repeat: {repeat}')

        suite_entry: dict[str, Any] = {
            'mode': mode,
            'filter': name_filter,
            'repeat': repeat,
            'cases': [],
        }
        if mode == 'search':
            suite_entry['depths'] = list(entry['depths'])

        for case in selected_cases:
            print(f'[{case.category}] {case.name}')
            if case.notes:
                print(f'  notes: {case.notes}')

            case_entry: dict[str, Any] = {
                'name': case.name,
                'category': case.category,
            }
            if case.notes:
                case_entry['notes'] = case.notes

            if mode == 'search':
                summaries: list[dict[str, Any]] = []
                for depth in entry['depths']:
                    summary = run_search_case(case, depth, repeat, args.diagnostics)
                    print_search_summary(summary, args.top)
                    summaries.append(summary_report_data(summary, args.top))
                case_entry['summaries'] = summaries
            elif mode in {'moves', 'tactical-moves'}:
                summary = run_movegen_case(case, repeat, tactical_only=mode == 'tactical-moves')
                print_movegen_summary(summary, args.top)
                case_entry['summary'] = summary_report_data(summary, args.top)
            else:
                summary = run_eval_case(case, repeat)
                print_eval_summary(summary)
                case_entry['summary'] = summary_report_data(summary, args.top)

            suite_entry['cases'].append(case_entry)

            print()

        suite_entries.append(suite_entry)

    if args.output:
        write_yaml_report(
            args.output,
            {
                'version': 1,
                'kind': 'pyengine2-benchmark-suite',
                'suite': args.suite,
                'pyengine2Version': PYENGINE2_VERSION,
                'benchmarkFile': str(args.file),
                'generatedAt': datetime.now(timezone.utc).isoformat(),
                'topCount': args.top,
                'diagnostics': bool(args.diagnostics),
                'entries': suite_entries,
            },
        )
        print(f'Wrote YAML report: {args.output}')

    return 0


def main() -> int:
    args = parse_args()
    cases = load_benchmarks(args.file)

    if args.name_filter:
        needle = args.name_filter.lower()
        cases = [case for case in cases if needle in case.name.lower()]

    if not cases:
        print('No benchmark cases selected.')
        return 1

    if args.suite:
        return run_suite(args, cases)

    print(f'Benchmark file: {args.file}')
    if args.mode == 'search':
        print(f'Mode: {args.mode} | Cases: {len(cases)} | Depths: {", ".join(str(depth) for depth in args.depths)} | Repeat: {args.repeat}')
    else:
        print(f'Mode: {args.mode} | Cases: {len(cases)} | Repeat: {args.repeat}')
    print()

    report_cases: list[dict[str, Any]] = []

    for case in cases:
        print(f'[{case.category}] {case.name}')
        if case.notes:
            print(f'  notes: {case.notes}')

        case_entry: dict[str, Any] = {
            'name': case.name,
            'category': case.category,
        }
        if case.notes:
            case_entry['notes'] = case.notes

        if args.mode == 'search':
            summaries: list[dict[str, Any]] = []
            for depth in args.depths:
                summary = run_search_case(case, depth, args.repeat, args.diagnostics)
                print_search_summary(summary, args.top)
                summaries.append(summary_report_data(summary, args.top))
            case_entry['summaries'] = summaries
        elif args.mode in {'moves', 'tactical-moves'}:
            summary = run_movegen_case(case, args.repeat, tactical_only=args.mode == 'tactical-moves')
            print_movegen_summary(summary, args.top)
            case_entry['summary'] = summary_report_data(summary, args.top)
        else:
            summary = run_eval_case(case, args.repeat)
            print_eval_summary(summary)
            case_entry['summary'] = summary_report_data(summary, args.top)

        report_cases.append(case_entry)

        print()

    if args.output:
        payload: dict[str, Any] = {
            'version': 1,
            'kind': 'pyengine2-benchmark-run',
            'pyengine2Version': PYENGINE2_VERSION,
            'benchmarkFile': str(args.file),
            'generatedAt': datetime.now(timezone.utc).isoformat(),
            'mode': args.mode,
            'repeat': args.repeat,
            'topCount': args.top,
            'diagnostics': bool(args.diagnostics),
            'cases': report_cases,
        }
        if args.mode == 'search':
            payload['depths'] = list(args.depths)
        if args.name_filter:
            payload['filter'] = args.name_filter
        write_yaml_report(args.output, payload)
        print(f'Wrote YAML report: {args.output}')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())