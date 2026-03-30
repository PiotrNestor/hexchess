from __future__ import annotations

import argparse
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pyengine2.native_engine import Hexchess, San
from pyengine2.version import PYENGINE2_VERSION


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RESULTS_DIR = ROOT_DIR / 'results' / PYENGINE2_VERSION
DEFAULT_BENCHMARK_FILE = ROOT_DIR / 'pyengine2' / 'benchmark' / 'benchmarks.yaml'
METRIC_FIELDS = (
    'wallMs',
    'evalsPerMs',
    'rootMoves',
    'negamaxNodes',
    'quiescenceNodes',
    'movegenCalls',
    'tacticalMovegenCalls',
    'legalContextCalls',
    'ttHits',
    'ttCutoffs',
    'betaCutoffs',
    'negamaxTtHits',
    'quiescenceTtHits',
    'negamaxTtCutoffs',
    'quiescenceTtCutoffs',
    'negamaxBetaCutoffs',
    'quiescenceBetaCutoffs',
    'qsearchStandPatCutoffs',
    'qsearchDeltaPruneChecks',
    'qsearchDeltaPruneSkips',
    'qsearchNodesWithMoves',
    'qsearchGeneratedMoves',
    'pvsResearches',
    'negamaxFrontierFutilityChecks',
    'negamaxFrontierFutilitySkips',
    'ttEntries',
        'nullMoveAttempts',
        'nullMoveCutoffs',
)
TAG_PRIORITY = (
    'tt-heavy',
    'qsearch-heavy',
    'movegen-heavy',
    'pruning-heavy',
    'wide-root',
    'node-heavy',
    'low-throughput',
    'slow-search',
)


@dataclass(frozen=True, slots=True)
class AnalyzedMove:
    game_file: Path
    ply: int
    san: str
    source: str
    before_fen: str
    after_fen: str
    wall_ms: float
    evals_per_ms: float
    root_moves: int
    negamax_nodes: int
    quiescence_nodes: int
    movegen_calls: int
    tactical_movegen_calls: int
    legal_context_calls: int
    tt_hits: int
    tt_cutoffs: int
    beta_cutoffs: int
    tt_entries: int
    duration_ms: float | None
    evaluations: int | None
    turn: str
    fullmove: int
    qsearch_ratio: float
    tags: tuple[str, ...] = ()
    dominant_tag: str = 'interesting'
    interestingness: float = 0.0

    def metrics_dict(self) -> dict[str, int | float | None]:
        return {
            'wallMs': self.wall_ms,
            'evalsPerMs': self.evals_per_ms,
            'rootMoves': self.root_moves,
            'negamaxNodes': self.negamax_nodes,
            'quiescenceNodes': self.quiescence_nodes,
            'movegenCalls': self.movegen_calls,
            'tacticalMovegenCalls': self.tactical_movegen_calls,
            'legalContextCalls': self.legal_context_calls,
            'ttHits': self.tt_hits,
            'ttCutoffs': self.tt_cutoffs,
            'betaCutoffs': self.beta_cutoffs,
            'ttEntries': self.tt_entries,
            'duration': self.duration_ms,
            'evaluations': self.evaluations,
            'qsearchRatio': self.qsearch_ratio,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Analyze saved pyengine2 game logs and extract benchmark candidates.')
    parser.add_argument('paths', type=Path, nargs='*', help='Game log files or directories to analyze')
    parser.add_argument('--source', default='python-api', help='Move source to analyze for engine metrics')
    parser.add_argument('--top', type=int, default=8, help='How many top examples to show per report section')
    parser.add_argument('--min-wall-ms', type=float, default=0.0, help='Ignore engine moves below this wall time when extracting candidates')
    parser.add_argument('--min-ply-gap', type=int, default=6, help='Minimum ply spacing for candidate diversity within the same game')
    parser.add_argument('--benchmark-output', type=Path, help='Write extracted benchmark candidates as YAML')
    parser.add_argument('--merge-benchmarks', type=Path, help='Merge selected candidates directly into a benchmark YAML file')
    parser.add_argument('--report-output', type=Path, help='Write the analysis report as YAML')
    return parser.parse_args()


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * quantile))
    return ordered[max(0, min(index, len(ordered) - 1))]


def _safe_mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _safe_median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _safe_max(values: list[float]) -> float:
    return max(values) if values else 0.0


def _slugify(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')


def _normalize(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return value / maximum


def _low_throughput_score(value: float, maximum: float) -> float:
    if maximum <= 0:
        return 0.0
    return max(0.0, 1.0 - (value / maximum))


def discover_game_files(paths: list[Path]) -> list[Path]:
    requested = paths or [DEFAULT_RESULTS_DIR]
    discovered: list[Path] = []
    for path in requested:
        if path.is_dir():
            discovered.extend(sorted(candidate for candidate in path.rglob('*.yaml') if candidate.is_file()))
        elif path.is_file():
            discovered.append(path)
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in discovered:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(path)
    return unique


def _read_cached_before_fen(item: dict[str, Any], canonical_before_fen: str, path: Path, ply: int, san_value: str) -> str:
    saved_before_fen = item.get('beforeFen')
    if not isinstance(saved_before_fen, str):
        return canonical_before_fen
    if saved_before_fen != canonical_before_fen:
        print(
            f'Warning: beforeFen mismatch in {path.name} ply {ply} ({san_value}); '
            'using canonical replay position from startFen + SAN.'
        )
        return canonical_before_fen
    return saved_before_fen


def load_game_file(path: Path, source: str) -> tuple[dict[str, Any], list[AnalyzedMove]]:
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or raw.get('version') != 1:
        raise ValueError(f'Unsupported game log format: {path}')
    start_fen = raw.get('startFen')
    moves = raw.get('moves')
    if not isinstance(start_fen, str) or not isinstance(moves, list):
        raise ValueError(f'Invalid game log contents: {path}')

    position = Hexchess.parse(start_fen)
    analyzed_moves: list[AnalyzedMove] = []

    for ply, item in enumerate(moves, start=1):
        if not isinstance(item, dict):
            raise ValueError(f'Invalid move entry at ply {ply}: {path}')
        san_value = item.get('san')
        if not isinstance(san_value, str):
            raise ValueError(f'Invalid SAN at ply {ply}: {path}')

        canonical_before_fen = position.to_string()
        before_fen = _read_cached_before_fen(item, canonical_before_fen, path, ply, san_value)
        turn = 'w' if position.turn == 0 else 'b'
        fullmove = position.fullmove
        next_position = position.clone()
        next_position.apply_move(San.parse(san_value))
        after_fen = next_position.to_string()

        move_source = item.get('source')
        metrics = item.get('metrics')
        if move_source == source and isinstance(metrics, dict):
            analyzed_moves.append(
                AnalyzedMove(
                    game_file=path,
                    ply=ply,
                    san=san_value,
                    source=source,
                    before_fen=before_fen,
                    after_fen=after_fen,
                    wall_ms=float(metrics.get('wallMs', 0.0)),
                    evals_per_ms=float(metrics.get('evalsPerMs', 0.0)),
                    root_moves=int(metrics.get('rootMoves', 0)),
                    negamax_nodes=int(metrics.get('negamaxNodes', 0)),
                    quiescence_nodes=int(metrics.get('quiescenceNodes', 0)),
                    movegen_calls=int(metrics.get('movegenCalls', 0)),
                    tactical_movegen_calls=int(metrics.get('tacticalMovegenCalls', 0)),
                    legal_context_calls=int(metrics.get('legalContextCalls', 0)),
                    tt_hits=int(metrics.get('ttHits', 0)),
                    tt_cutoffs=int(metrics.get('ttCutoffs', 0)),
                    beta_cutoffs=int(metrics.get('betaCutoffs', 0)),
                    tt_entries=int(metrics.get('ttEntries', 0)),
                    duration_ms=float(item['duration']) if isinstance(item.get('duration'), (int, float)) else None,
                    evaluations=int(item['evaluations']) if isinstance(item.get('evaluations'), int) else None,
                    turn=turn,
                    fullmove=fullmove,
                    qsearch_ratio=float(metrics.get('quiescenceNodes', 0)) / max(int(metrics.get('negamaxNodes', 0)), 1),
                )
            )

        position = next_position

    return raw, analyzed_moves


def annotate_moves(moves: list[AnalyzedMove]) -> list[AnalyzedMove]:
    if not moves:
        return []

    wall_threshold = _percentile([move.wall_ms for move in moves], 0.8)
    negamax_threshold = _percentile([float(move.negamax_nodes) for move in moves], 0.8)
    quiescence_threshold = _percentile([float(move.quiescence_nodes) for move in moves], 0.8)
    qratio_threshold = _percentile([move.qsearch_ratio for move in moves], 0.8)
    tt_hits_threshold = _percentile([float(move.tt_hits) for move in moves], 0.8)
    movegen_threshold = _percentile([float(move.movegen_calls) for move in moves], 0.8)
    beta_threshold = _percentile([float(move.beta_cutoffs) for move in moves], 0.8)
    root_threshold = _percentile([float(move.root_moves) for move in moves], 0.8)
    slow_evals_threshold = _percentile([move.evals_per_ms for move in moves], 0.2)

    max_wall = _safe_max([move.wall_ms for move in moves])
    max_negamax = _safe_max([float(move.negamax_nodes) for move in moves])
    max_quiescence = _safe_max([float(move.quiescence_nodes) for move in moves])
    max_tt_hits = _safe_max([float(move.tt_hits) for move in moves])
    max_movegen = _safe_max([float(move.movegen_calls) for move in moves])
    max_beta = _safe_max([float(move.beta_cutoffs) for move in moves])
    max_qratio = _safe_max([move.qsearch_ratio for move in moves])
    max_root = _safe_max([float(move.root_moves) for move in moves])
    max_evals_per_ms = _safe_max([move.evals_per_ms for move in moves])

    annotated: list[AnalyzedMove] = []
    for move in moves:
        tags: list[str] = []
        if move.wall_ms >= wall_threshold:
            tags.append('slow-search')
        if move.negamax_nodes >= negamax_threshold:
            tags.append('node-heavy')
        if move.quiescence_nodes >= quiescence_threshold or move.qsearch_ratio >= qratio_threshold:
            tags.append('qsearch-heavy')
        if move.tt_hits >= tt_hits_threshold:
            tags.append('tt-heavy')
        if move.movegen_calls >= movegen_threshold:
            tags.append('movegen-heavy')
        if move.beta_cutoffs >= beta_threshold:
            tags.append('pruning-heavy')
        if move.root_moves >= root_threshold:
            tags.append('wide-root')
        if move.evals_per_ms <= slow_evals_threshold:
            tags.append('low-throughput')

        category_scores = {
            'slow-search': _normalize(move.wall_ms, max_wall),
            'node-heavy': _normalize(float(move.negamax_nodes), max_negamax),
            'qsearch-heavy': max(_normalize(float(move.quiescence_nodes), max_quiescence), _normalize(move.qsearch_ratio, max_qratio)),
            'tt-heavy': _normalize(float(move.tt_hits), max_tt_hits),
            'movegen-heavy': _normalize(float(move.movegen_calls), max_movegen),
            'pruning-heavy': _normalize(float(move.beta_cutoffs), max_beta),
            'wide-root': _normalize(float(move.root_moves), max_root),
            'low-throughput': _low_throughput_score(move.evals_per_ms, max_evals_per_ms),
        }
        tagged_scores = [(tag, category_scores[tag]) for tag in tags] or [('interesting', 0.0)]
        dominant_tag = max(
            tagged_scores,
            key=lambda item: (item[1], -TAG_PRIORITY.index(item[0]) if item[0] in TAG_PRIORITY else 0),
        )[0]

        interestingness = (
            2.0 * _normalize(move.wall_ms, max_wall)
            + 1.2 * _normalize(float(move.negamax_nodes), max_negamax)
            + 1.2 * _normalize(float(move.quiescence_nodes), max_quiescence)
            + 0.9 * _normalize(float(move.tt_hits), max_tt_hits)
            + 0.8 * _normalize(float(move.movegen_calls), max_movegen)
            + 0.8 * _normalize(float(move.beta_cutoffs), max_beta)
            + 0.8 * _normalize(move.qsearch_ratio, max_qratio)
        )

        annotated.append(
            AnalyzedMove(
                game_file=move.game_file,
                ply=move.ply,
                san=move.san,
                source=move.source,
                before_fen=move.before_fen,
                after_fen=move.after_fen,
                wall_ms=move.wall_ms,
                evals_per_ms=move.evals_per_ms,
                root_moves=move.root_moves,
                negamax_nodes=move.negamax_nodes,
                quiescence_nodes=move.quiescence_nodes,
                movegen_calls=move.movegen_calls,
                tactical_movegen_calls=move.tactical_movegen_calls,
                legal_context_calls=move.legal_context_calls,
                tt_hits=move.tt_hits,
                tt_cutoffs=move.tt_cutoffs,
                beta_cutoffs=move.beta_cutoffs,
                tt_entries=move.tt_entries,
                duration_ms=move.duration_ms,
                evaluations=move.evaluations,
                turn=move.turn,
                fullmove=move.fullmove,
                qsearch_ratio=move.qsearch_ratio,
                tags=tuple(tags),
                dominant_tag=dominant_tag,
                interestingness=interestingness,
            )
        )

    return annotated


def _candidate_conflicts(candidate: AnalyzedMove, selected: list[AnalyzedMove], min_ply_gap: int) -> bool:
    for existing in selected:
        if existing.before_fen == candidate.before_fen:
            return True
        if existing.game_file == candidate.game_file and abs(existing.ply - candidate.ply) < min_ply_gap:
            return True
    return False


def select_candidates(moves: list[AnalyzedMove], top: int, min_wall_ms: float, min_ply_gap: int) -> list[AnalyzedMove]:
    eligible = [move for move in moves if move.wall_ms >= min_wall_ms]
    if not eligible:
        return []

    selected: list[AnalyzedMove] = []
    grouped: dict[str, list[AnalyzedMove]] = defaultdict(list)
    for move in sorted(eligible, key=lambda item: item.interestingness, reverse=True):
        grouped[move.dominant_tag].append(move)

    for tag in TAG_PRIORITY:
        for move in grouped.get(tag, []):
            if _candidate_conflicts(move, selected, min_ply_gap):
                continue
            selected.append(move)
            break
        if len(selected) >= top:
            return selected

    pools: list[AnalyzedMove] = []
    for sorter in (
        lambda move: move.interestingness,
        lambda move: move.wall_ms,
        lambda move: move.negamax_nodes,
        lambda move: move.quiescence_nodes,
        lambda move: move.tt_hits,
        lambda move: move.movegen_calls,
        lambda move: move.qsearch_ratio,
        lambda move: move.beta_cutoffs,
    ):
        pools.extend(sorted(eligible, key=sorter, reverse=True)[: max(3, top)])

    seen_primary_tags = {move.dominant_tag for move in selected}
    for move in sorted(pools, key=lambda item: (item.dominant_tag not in seen_primary_tags, item.interestingness), reverse=True):
        if _candidate_conflicts(move, selected, min_ply_gap):
            continue
        selected.append(move)
        seen_primary_tags.add(move.dominant_tag)
        if len(selected) >= top:
            break

    return selected


def _unique_name(name: str, existing_names: set[str]) -> str:
    if name not in existing_names:
        return name
    suffix = 2
    while f'{name}-{suffix}' in existing_names:
        suffix += 1
    return f'{name}-{suffix}'


def benchmark_entry_for(move: AnalyzedMove) -> dict[str, str]:
    primary_tag = move.dominant_tag if move.dominant_tag else 'interesting'
    file_stem = _slugify(move.game_file.stem)
    notes = (
        f'Harvested from {move.game_file.name} before ply {move.ply} ({move.turn}{move.fullmove} {move.san}). '
        f'tags: {", ".join(move.tags) if move.tags else "interesting"}. '
        f'wallMs={move.wall_ms:.1f}, negamaxNodes={move.negamax_nodes}, '
        f'quiescenceNodes={move.quiescence_nodes}, ttHits={move.tt_hits}, movegenCalls={move.movegen_calls}.'
    )
    return {
        'name': f'harvested-{file_stem}-ply-{move.ply:03d}-{primary_tag}',
        'category': 'harvested',
        'fen': move.before_fen,
        'notes': notes,
    }


def merge_candidates_into_benchmarks(path: Path, candidates: list[AnalyzedMove]) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or raw.get('version') != 1 or not isinstance(raw.get('benchmarks'), list):
        raise ValueError(f'Unsupported benchmark file format: {path}')

    benchmarks = raw['benchmarks']
    existing_names = {item.get('name') for item in benchmarks if isinstance(item, dict) and isinstance(item.get('name'), str)}
    existing_fens = {item.get('fen') for item in benchmarks if isinstance(item, dict) and isinstance(item.get('fen'), str)}

    added: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    for move in candidates:
        entry = benchmark_entry_for(move)
        fen = entry['fen']
        if fen in existing_fens:
            skipped.append({'reason': 'duplicate-fen', 'name': entry['name'], 'fen': fen})
            continue

        entry['name'] = _unique_name(entry['name'], existing_names)
        existing_names.add(entry['name'])
        existing_fens.add(fen)
        benchmarks.append(entry)
        added.append(entry)

    path.write_text(yaml.safe_dump(raw, sort_keys=False, allow_unicode=False), encoding='utf-8')
    return {
        'path': str(path),
        'added': added,
        'skipped': skipped,
    }


def summarize_moves(moves: list[AnalyzedMove]) -> dict[str, dict[str, float]]:
    summary: dict[str, dict[str, float]] = {}
    for field in ('wall_ms', 'evals_per_ms', 'negamax_nodes', 'quiescence_nodes', 'tt_hits', 'beta_cutoffs', 'movegen_calls', 'qsearch_ratio'):
        values = [float(getattr(move, field)) for move in moves]
        summary[field] = {
            'mean': _safe_mean(values),
            'median': _safe_median(values),
            'max': _safe_max(values),
        }
    return summary


def top_section(moves: list[AnalyzedMove], key: str, top: int) -> list[dict[str, Any]]:
    ordered = sorted(moves, key=lambda move: getattr(move, key), reverse=True)[:top]
    return [
        {
            'game': move.game_file.name,
            'ply': move.ply,
            'turn': move.turn,
            'fullmove': move.fullmove,
            'san': move.san,
            'value': getattr(move, key),
            'wallMs': move.wall_ms,
            'dominantTag': move.dominant_tag,
            'tags': list(move.tags),
        }
        for move in ordered
    ]


def print_report(files: list[Path], total_moves: int, analyzed_moves: list[AnalyzedMove], candidates: list[AnalyzedMove], top: int, merge_summary: dict[str, Any] | None = None) -> None:
    print(f'pyengine2 version: {PYENGINE2_VERSION}')
    print(f'Game files analyzed: {len(files)}')
    print(f'Total logged plies: {total_moves}')
    print(f'Engine plies with metrics: {len(analyzed_moves)}')
    print()

    if not analyzed_moves:
        print('No engine moves with metrics were found for the selected source.')
        return

    summary = summarize_moves(analyzed_moves)
    print('Metric summary:')
    for key, values in summary.items():
        label = key.replace('_', ' ')
        print(f'  {label}: mean={values["mean"]:.2f}, median={values["median"]:.2f}, max={values["max"]:.2f}')
    print()

    sections = (
        ('Top by wallMs', 'wall_ms'),
        ('Top by negamaxNodes', 'negamax_nodes'),
        ('Top by quiescenceNodes', 'quiescence_nodes'),
        ('Top by ttHits', 'tt_hits'),
        ('Top by qsearchRatio', 'qsearch_ratio'),
    )
    for title, field in sections:
        print(f'{title}:')
        for item in top_section(analyzed_moves, field, top):
            print(
                f'  ply {item["ply"]:>3} | {item["game"]} | {item["san"]} | '
                f'value={item["value"]:.2f} | wallMs={item["wallMs"]:.1f} | dominant={item["dominantTag"]} | tags={", ".join(item["tags"]) or "-"}'
            )
        print()

    print('Benchmark candidates:')
    for move in candidates:
        print(
            f'  ply {move.ply:>3} | {move.game_file.name} | {move.san} | '
            f'wallMs={move.wall_ms:.1f} | qRatio={move.qsearch_ratio:.2f} | '
            f'dominant={move.dominant_tag} | tags={", ".join(move.tags) or "interesting"}'
        )

    if merge_summary is not None:
        print()
        print(f'Merged into benchmark file: {merge_summary["path"]}')
        print(f'  added: {len(merge_summary["added"])}')
        print(f'  skipped: {len(merge_summary["skipped"])}')


def build_report(files: list[Path], raw_games: list[dict[str, Any]], analyzed_moves: list[AnalyzedMove], candidates: list[AnalyzedMove], top: int, merge_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        'version': 1,
        'pyengine2Version': PYENGINE2_VERSION,
        'files': [str(path) for path in files],
        'gameCount': len(raw_games),
        'totalLoggedPlies': sum(len(game.get('moves', [])) for game in raw_games),
        'enginePliesWithMetrics': len(analyzed_moves),
        'metricSummary': summarize_moves(analyzed_moves),
        'topWallMs': top_section(analyzed_moves, 'wall_ms', top),
        'topNegamaxNodes': top_section(analyzed_moves, 'negamax_nodes', top),
        'topQuiescenceNodes': top_section(analyzed_moves, 'quiescence_nodes', top),
        'topTtHits': top_section(analyzed_moves, 'tt_hits', top),
        'topQsearchRatio': top_section(analyzed_moves, 'qsearch_ratio', top),
        'benchmarkCandidates': [
            {
                'game': move.game_file.name,
                'ply': move.ply,
                'san': move.san,
                'tags': list(move.tags),
                'dominantTag': move.dominant_tag,
                'interestingness': move.interestingness,
                'fen': move.before_fen,
                'metrics': move.metrics_dict(),
                'benchmark': benchmark_entry_for(move),
            }
            for move in candidates
        ],
        'mergeSummary': merge_summary,
    }


def main() -> int:
    args = parse_args()
    files = discover_game_files(args.paths)
    if not files:
        print('No game log files selected.')
        return 1

    raw_games: list[dict[str, Any]] = []
    analyzed_moves: list[AnalyzedMove] = []
    total_moves = 0
    for path in files:
        raw_game, game_moves = load_game_file(path, args.source)
        raw_games.append(raw_game)
        total_moves += len(raw_game.get('moves', []))
        analyzed_moves.extend(game_moves)

    annotated_moves = annotate_moves(analyzed_moves)
    candidates = select_candidates(annotated_moves, args.top, args.min_wall_ms, args.min_ply_gap)
    merge_summary = merge_candidates_into_benchmarks(args.merge_benchmarks or DEFAULT_BENCHMARK_FILE, candidates) if args.merge_benchmarks else None
    report = build_report(files, raw_games, annotated_moves, candidates, args.top, merge_summary)

    print_report(files, total_moves, annotated_moves, candidates, args.top, merge_summary)

    if args.report_output:
        args.report_output.parent.mkdir(parents=True, exist_ok=True)
        args.report_output.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=False), encoding='utf-8')

    if args.benchmark_output:
        args.benchmark_output.parent.mkdir(parents=True, exist_ok=True)
        payload = {'version': 1, 'benchmarks': [benchmark_entry_for(move) for move in candidates]}
        args.benchmark_output.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding='utf-8')

    return 0


if __name__ == '__main__':
    raise SystemExit(main())