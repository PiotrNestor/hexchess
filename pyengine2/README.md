# pyengine2

Current version: `2.1.003`

`pyengine2` is the current Python-native hexchess engine implementation in this repository.

Versioning for `pyengine2` is tracked independently in a simple `2.1.nnn` format so engine progress can be recorded explicitly during optimization work.

Its generic engine shape starts from the same broad design ideas used by the Rust hexchess engine: a compact board representation, precomputed board data, a search-oriented move format, and a clean API boundary between engine logic and transport. This implementation does not wrap another engine. The search, move generation, evaluation, and API behavior are implemented directly in Python.

## Design Overview

The engine is built around a numeric core instead of a string-heavy rules layer.

- board state is stored as integer piece codes in a fixed-size board array
- per-piece and per-color occupancy masks are maintained alongside the board
- moves are packed into integer move codes for search and internal transport
- search uses a negamax core with alpha-beta pruning, principal variation search, and quiescence search
- repeated positions are reused through a Zobrist-keyed transposition table in both negamax and quiescence
- legal move generation is search-oriented and uses precomputed board geometry
- the FastAPI wrapper exposes the same command-style engine contract used elsewhere in the project

At the current stage, the engine design can be summarized as:

- a Python-native numeric search core rather than a SAN-first rules engine
- low-allocation search state through reusable per-ply move buffers
- array-backed history and killer heuristics in `SearchState` to avoid dict and tuple churn in deep search
- specialized move builders for pawns, knights, bishops, rooks, queens, and king moves
- occupancy-indexed slider lookups instead of per-ray walking in the hot path
- direct king-safety legality filtering during generation
- transposition-table reuse in both full search and qsearch
- TT-aware internal move ordering for both full search and tactical qsearch move lists
- conservative qsearch delta pruning that only activates when the alpha gap is wide enough to justify the extra filter cost
- per-search metrics emission for wall time, node counts, movegen calls, TT hits, and cutoffs
- root-stable public move ordering separated from the faster internal search path

The current code is split mainly across these files:

- [pyengine2/native_engine.py](pyengine2/native_engine.py): engine core, search, move generation, evaluation, and command execution
- [pyengine2/main.py](pyengine2/main.py): FastAPI wrapper for `/execute`, `/hexchess/ping`, and `/health`
- [pyengine2/benchmark.py](pyengine2/benchmark.py): search and move-generation benchmark runner
- [pyengine2/test_native_engine.py](pyengine2/test_native_engine.py): regression-focused unit tests
- [pyengine2/board_constants.py](pyengine2/board_constants.py): pure-Python board graph and starting-position constants

## How To Run

### Run the API server

From the repository root:

```powershell
python -m uvicorn pyengine2.main:app --reload
```

Useful endpoints:

- `GET /health`
- `GET /hexchess/ping`
- `POST /execute`

The API wrapper delegates engine work to `execute_command(...)` in [pyengine2/native_engine.py](pyengine2/native_engine.py).

For `hexchess/evaluate`, callers may optionally provide `options.positionHistory` as a list of earlier FEN strings from the same game. `pyengine2` uses that prior-position history to score threefold-repetition lines as draws instead of treating them as ordinary fresh positions.

### Run the benchmark suite

Search benchmarks:

```powershell
python pyengine2/benchmark.py --depths 2 3 4 --repeat 3
```

Full legal move-generation benchmarks:

```powershell
python pyengine2/benchmark.py --mode moves --repeat 10
```

Tactical-only move-generation benchmarks:

```powershell
python pyengine2/benchmark.py --mode tactical-moves --repeat 10
```

Static-evaluation benchmarks:

```powershell
python pyengine2/benchmark.py --mode eval --repeat 50
```

Stage 1 baseline suite:

```powershell
python pyengine2/benchmark.py --suite stage1-baseline
```

Stage 1 baseline suite with YAML report output:

```powershell
python pyengine2/benchmark.py --suite stage1-baseline --output results/2.1.003/stage1-baseline.yaml
```

Harvested diagnostic suite with engine counters enabled:

```powershell
python pyengine2/benchmark.py --suite harvested-diagnostics --diagnostics --output results/2.1.003/harvested-diagnostics.yaml
```

Historical harvested diagnostic suite for the March 24 and March 26 positions:

```powershell
python pyengine2/benchmark.py --suite harvested-history-diagnostics --diagnostics --output results/2.1.003/harvested-history-diagnostics.yaml
```

Clean search-comparison suite for keep-or-revert decisions on search changes:

```powershell
python pyengine2/benchmark.py --suite clean-search-comparison --output results/2.1.003/clean-search-comparison.yaml
```

Saved game analysis:

```powershell
python pyengine2/analyze_game.py results/2.1.003
```

Benchmark-candidate export from saved games:

```powershell
python pyengine2/analyze_game.py results/2.1.003 --benchmark-output results/2.1.003/benchmark-candidates.yaml --report-output results/2.1.003/game-analysis.yaml
```

Direct merge into the benchmark corpus:

```powershell
python pyengine2/analyze_game.py results/2.1.003 --merge-benchmarks pyengine2/benchmark/benchmarks.yaml --report-output results/2.1.003/game-analysis.yaml
```

This suite reruns the current Stage 1 comparison set in one command:

- quiet eval cost
- slider-heavy full move generation
- tactical-only move generation
- TT-sensitive search at depths 4 and 5
- qsearch-heavy search at depths 4 and 5
- opening baseline at depths 4 and 5

The harvested diagnostic suite is separate on purpose. It samples the March 29 harvested stress positions for TT-heavy, qsearch-heavy, wide-root, node-heavy, and low-throughput behavior at depth 3 with single-run diagnostics, so those cases stay easy to rerun without changing the official clean baseline.

The historical harvested diagnostic suite extends that same depth-3 single-run diagnostic pass across the March 24 and March 26 harvested positions, so the full harvested corpus can be rerun with two commands instead of one large ad hoc filter list.

The clean search-comparison suite is the search-only keep-or-revert set. It keeps the Stage 1 baseline intact, but adds the March 29 TT-heavy position alongside the existing clean comparison cases so search regressions are less likely to hide behind opening-only or qsearch-only behavior.

When `--output` is provided, the benchmark runner writes a YAML report for either a suite run or a regular filtered benchmark run. This is intended for versioned baseline snapshots under `results/<pyengine2-version>/`.

The benchmark runner currently supports these benchmark features:

- filtered runs by benchmark name with `--filter`
- four measurement modes: `search`, `moves`, `tactical-moves`, and `eval`
- predefined suite execution with `--suite stage1-baseline`, `--suite clean-search-comparison`, `--suite harvested-diagnostics`, or `--suite harvested-history-diagnostics`
- YAML report output for suite and non-suite runs with `--output`
- search summaries that include top moves and engine metrics in the saved YAML output
- a benchmark corpus that can be extended manually or by harvested-game extraction

The saved-game analyzer replays Sandbox game logs, summarizes pyengine2 move metrics, extracts benchmark-candidate FEN positions from the most interesting engine plies, and can merge selected harvested candidates directly into the benchmark corpus with FEN and name dedupe checks.

Saved game logs may also include optional `beforeFen` metadata per move. This is treated as cached convenience state for analysis and debugging only. The canonical source of truth remains `startFen` plus SAN replay.

You can narrow to a specific benchmark case with `--filter`, for example:

```powershell
python pyengine2/benchmark.py --mode tactical-moves --filter capture-storm-qsearch --repeat 10
```

## Benchmark Procedure

The benchmark workflow is intended to answer a specific question: did a change improve the full engine, the full legal move generator, the tactical-only generator, or none of them?

Use the same procedure after each meaningful search or move-generation change.

### 1. Re-run unit tests first

Before trusting any benchmark result, confirm that the engine still passes the regression suite.

```powershell
python -m unittest pyengine2.test_native_engine
```

### 2. Measure the tactical-only generator first

Run the tactical-only benchmark on the capture-dense qsearch case.

```powershell
python pyengine2/benchmark.py --mode tactical-moves --filter capture-storm-qsearch --repeat 10
```

Use this when changing:

- qsearch move generation
- tactical move ordering
- capture and promotion filtering

If this regresses while full move generation stays flat, the problem is likely in the tactical-only path rather than the broader legal generator.

### 3. Measure the full legal move generator next

Use the full move-generation mode on targeted cases.

Pinned and defensive filtering:

```powershell
python pyengine2/benchmark.py --mode moves --filter pinned-defense --repeat 10
python pyengine2/benchmark.py --mode moves --filter double-check-defense --repeat 10
```

Pawn-specialized paths:

```powershell
python pyengine2/benchmark.py --mode moves --filter promotion-race --repeat 10
python pyengine2/benchmark.py --mode moves --filter en-passant --repeat 10
```

Slider-heavy path:

```powershell
python pyengine2/benchmark.py --mode moves --filter slider-mobility-open --repeat 10
```

Use these after changing:

- `_fill_current_moves(...)`
- legal-context computation
- pin handling
- pawn generation
- promotion and en passant logic

If these regress but `search` results stay noisy or ambiguous, trust these mode-level measurements first. They are better at exposing low-level generator cost directly.

### 4. Measure the tactical search case under real search

After isolated generator checks, run a full search benchmark on the qsearch-heavy case.

```powershell
python pyengine2/benchmark.py --filter capture-storm-qsearch --depths 2 3 4 --repeat 3
```

This tells you whether the isolated generator change actually improves the broader search stack.

### 4a. Measure quiet eval cost directly when needed

If a change may affect leaf cost more than search control, measure static evaluation directly.

```powershell
python pyengine2/benchmark.py --mode eval --filter quiet-endgame-eval --repeat 50
```

This is useful after changing:

- `evaluate(...)`
- `static_eval_for_turn(...)`
- pawn or attacked-piece evaluation terms

### 5. Re-run the baseline opening ladder

Use the opening baseline as the final comparison point.

```powershell
python pyengine2/benchmark.py --filter initial-position --depths 2 3 4 --repeat 3
```

This is the main continuity benchmark for tracking overall engine speed over time.

### 5a. Re-run the TT-sensitive middlegame when search changes

For TT, PVS, or move-ordering changes, also run:

```powershell
python pyengine2/benchmark.py --filter tt-transposition-midgame --depths 2 3 4 --repeat 3
```

This case is intended to show whether search control changes improve repeated-position reuse and mid-tree ordering quality.

### 6. Compare the results by failure mode

Interpret benchmark changes in this order:

- `tactical-moves` regresses, `moves` is flat:
	the tactical-only path likely regressed
- `moves` regresses on `pinned-defense` or `double-check-defense`:
	legal-context or king-safety filtering likely regressed
- `moves` regresses on `promotion-race` or `en-passant-*`:
	pawn generation likely regressed
- `moves` improves but `search` does not:
	qsearch, evaluation, or search control is now the limiting factor
- `capture-storm-qsearch` changes but `initial-position` does not:
	the change is tactical-specific and not broad enough to move the general opening baseline yet
- `eval` regresses while `moves` and `tactical-moves` are flat:
	leaf evaluation cost likely regressed without a move-generation problem
- `tt-transposition-midgame` changes more than `initial-position`:
	the update is affecting TT reuse or move-order quality more than generic opening search

### Recommended Command Ladder

For most performance work, this is the default sequence:

```powershell
python -m unittest pyengine2.test_native_engine
python pyengine2/benchmark.py --mode eval --filter quiet-endgame-eval --repeat 50
python pyengine2/benchmark.py --mode moves --filter slider-mobility-open --repeat 10
python pyengine2/benchmark.py --mode tactical-moves --filter capture-storm-qsearch --repeat 10
python pyengine2/benchmark.py --mode moves --filter pinned-defense --repeat 10
python pyengine2/benchmark.py --mode moves --filter promotion-race --repeat 10
python pyengine2/benchmark.py --filter tt-transposition-midgame --depths 2 3 4 --repeat 3
python pyengine2/benchmark.py --filter capture-storm-qsearch --depths 2 3 4 --repeat 3
python pyengine2/benchmark.py --filter initial-position --depths 2 3 4 --repeat 3
```

This sequence is short enough to run after each meaningful optimization pass, but still detailed enough to separate search-level wins from generator-only wins.

For the current Stage 1 optimization track, the faster rerun command is:

```powershell
python pyengine2/benchmark.py --suite stage1-baseline
```

## How It Is Tested

### Unit tests

Run the regression suite from the repository root:

```powershell
python -m unittest pyengine2.test_native_engine
```

The unit tests currently cover:

- SAN parsing
- stable public move ordering
- search sanity at depth 1
- evaluation sanity
- legal and illegal en passant handling
- quiet and capture promotions
- double-check behavior
- pinned-piece legality
- parity between the fast internal legal-move generator and the public move list
- tactical-only move generation on a capture-dense position
- qsearch delta-pruning guard behavior for low-value captures, promotions, and TT-prioritized moves

### Benchmarks

Benchmarks are also part of the validation workflow when changing the engine.

The benchmark corpus lives in [pyengine2/benchmark/benchmarks.yaml](pyengine2/benchmark/benchmarks.yaml) and now includes:

- opening and middlegame search baselines
- in-check and defensive positions
- pinned-piece and double-check cases
- en passant legality cases
- promotion-heavy cases
- a capture-dense qsearch stress case
- a TT-sensitive middlegame case
- a quiet eval-heavy endgame case
- an open-board slider mobility case

These are used to distinguish between regressions in:

- full search throughput
- full legal move generation
- tactical-only move generation
- static evaluation cost

The benchmark runner currently supports these modes:

- `search`: full fixed-depth search with wall time, total evaluations, and `evals/ms`
- `moves`: full legal move generation with wall time, total generated moves, and `moves/ms`
- `tactical-moves`: tactical-only move generation with wall time, total generated moves, and `moves/ms`
- `eval`: repeated static evaluation with wall time, evaluation count, `evals/ms`, and median eval score

When YAML output is enabled, saved reports also include:

- suite metadata, runner version, benchmark corpus path, and generation timestamp
- per-case summaries for eval and movegen runs
- per-depth summaries for search runs
- top move samples for movegen and search modes
- engine metrics for search runs such as node counts, movegen calls, TT hits, TT cutoffs, and beta cutoffs

## Benchmark Status

The benchmark setup is now intended to separate five different kinds of changes:

- raw search-control improvements
- legal move-generation improvements
- tactical-only generation changes
- static evaluation cost changes
- changes that reduce search work and expose better TT or qsearch behavior in saved metrics

The primary saved Stage 1 baseline for the current version is [results/2.1.003/stage1-baseline.yaml](results/2.1.003/stage1-baseline.yaml).

At the time of writing, the current Stage 1 baseline is approximately:

- `quiet-endgame-eval` in `eval` mode: `0.0020 ms`
- `slider-mobility-open` in `moves` mode: `0.038 ms` for `114` moves
- `capture-storm-qsearch` in `tactical-moves` mode: `0.006 ms` for `3` moves
- `tt-transposition-midgame`, depth 4: `1194.3 ms` and `29,818` evaluations
- `tt-transposition-midgame`, depth 5: `5137.0 ms` and `97,117` evaluations
- `capture-storm-qsearch`, depth 4: `354.1 ms` and `8,880` evaluations
- `capture-storm-qsearch`, depth 5: `1076.8 ms` and `20,123` evaluations
- `initial-position`, depth 4: `6748.4 ms` and `140,300` evaluations
- `initial-position`, depth 5: `42787.1 ms` and `1,012,033` evaluations

These numbers are working comparison points on the current machine and environment, not fixed guarantees.

## Design Features So Far

The engine currently includes the following implemented design features.

- Python-native numeric board representation
- fixed piece-code board array with synchronized color and piece masks
- packed integer move encoding
- precomputed board graph and square metadata in pure Python
- precomputed king, knight, pawn, line, and ray attack data
- occupancy-indexed slider attack tables
- single-pass legal move generation for search
- piece-specialized move builders for pawns, knights, bishops, rooks, queens, and king moves
- direct king-safety filtering during move generation
- direct en passant legality handling without routing through full make/unmake in the hot path
- piece-mask-based evaluation
- quiescence search
- conservative qsearch delta pruning for clearly non-improving low-value tactical continuations
- principal variation search for non-root full-search siblings
- Zobrist-keyed transposition-table reuse in negamax
- Zobrist-keyed transposition-table reuse in quiescence with depth-safe replacement behavior
- reusable per-ply `SearchState` move buffers to reduce list churn
- reusable per-ply pin-mask buffers to avoid rebuilding legality scratch state
- fixed-size history-score arrays and per-ply killer slots for move ordering
- TT promotion and integer-score sorting in internal move ordering paths
- engine-side search metrics returned with search responses and persisted by Sandbox logs
- stable public move ordering kept separate from the faster internal search path
- FastAPI command wrapper compatible with the project engine contract
- benchmark modes for search, full move generation, tactical-only move generation, and static evaluation
- benchmark-suite YAML snapshots and saved-game analysis tooling for harvesting new benchmark cases

## Current Focus

Current optimization work is centered on:

- preserving current search-quality gains from TT, PVS, and qsearch pruning while reducing remaining hot-path cost
- using saved-game metrics and harvested positions to choose the next benchmark-backed optimization target
- continuing to measure tactical-only generation, leaf evaluation, and versioned Stage 1 baselines separately from full search
- keeping correctness locked down with targeted regression tests while search speed changes continue