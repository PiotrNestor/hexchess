# pyengine2

`pyengine2` is the current Python-native hexchess engine implementation in this repository.

Its generic engine shape starts from the same broad design ideas used by the Rust hexchess engine: a compact board representation, precomputed board data, a search-oriented move format, and a clean API boundary between engine logic and transport. This implementation does not wrap another engine. The search, move generation, evaluation, and API behavior are implemented directly in Python.

## Design Overview

The engine is built around a numeric core instead of a string-heavy rules layer.

- board state is stored as integer piece codes in a fixed-size board array
- per-piece and per-color occupancy masks are maintained alongside the board
- moves are packed into integer move codes for search and internal transport
- search uses a negamax core with alpha-beta pruning and quiescence search
- legal move generation is search-oriented and uses precomputed board geometry
- the FastAPI wrapper exposes the same command-style engine contract used elsewhere in the project

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

### 5. Re-run the baseline opening ladder

Use the opening baseline as the final comparison point.

```powershell
python pyengine2/benchmark.py --filter initial-position --depths 2 3 4 --repeat 3
```

This is the main continuity benchmark for tracking overall engine speed over time.

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

### Recommended Command Ladder

For most performance work, this is the default sequence:

```powershell
python -m unittest pyengine2.test_native_engine
python pyengine2/benchmark.py --mode tactical-moves --filter capture-storm-qsearch --repeat 10
python pyengine2/benchmark.py --mode moves --filter pinned-defense --repeat 10
python pyengine2/benchmark.py --mode moves --filter promotion-race --repeat 10
python pyengine2/benchmark.py --filter capture-storm-qsearch --depths 2 3 4 --repeat 3
python pyengine2/benchmark.py --filter initial-position --depths 2 3 4 --repeat 3
```

This sequence is short enough to run after each meaningful optimization pass, but still detailed enough to separate search-level wins from generator-only wins.

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

### Benchmarks

Benchmarks are also part of the validation workflow when changing the engine.

The benchmark corpus lives in [pyengine/benchmarks.yaml](pyengine/benchmarks.yaml) and now includes:

- opening and middlegame search baselines
- in-check and defensive positions
- pinned-piece and double-check cases
- en passant legality cases
- promotion-heavy cases
- a capture-dense qsearch stress case

These are used to distinguish between regressions in:

- full search throughput
- full legal move generation
- tactical-only move generation

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
- reusable per-ply `SearchState` move buffers to reduce list churn
- stable public move ordering kept separate from the faster internal search path
- FastAPI command wrapper compatible with the project engine contract
- benchmark modes for search, full move generation, and tactical-only move generation

## Current Focus

Current optimization work is centered on:

- reducing the cost of the full legal move-generation shell
- measuring tactical-only generation separately before the next qsearch pass
- keeping correctness locked down with targeted regression tests while search speed changes continue