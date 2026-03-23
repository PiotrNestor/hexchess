# pyengine

`pyengine` is the native Python implementation of the hexchess engine and HTTP API.

The search, move generation, evaluation, and API dispatch run directly inside Python and follow the engine API integration defined in this project.

## Current Status

The Python engine is already a real playable engine, not a bridge.

At this point it provides:

- FastAPI endpoint compatible with the existing engine request/response envelope
- native Python board representation and rule handling
- legal move generation for Gliński hexagonal chess
- negamax search with alpha-beta pruning
- quiescence search for tactical stabilization
- transposition table support
- move ordering heuristics


The implementation is functional and integrated into the project Sandbox, but it is still an actively tuned engine and should be treated as ongoing work rather than a finished engine.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r pyengine/requirements.txt
```

## Run

```bash
uvicorn pyengine.main:app --reload --host 127.0.0.1 --port 8000
```

## Implementation Summary

The engine lives primarily in [native_engine.py](g:/work/Training/hexchess/pyengine/native_engine.py) and is exposed through [main.py](g:/work/Training/hexchess/pyengine/main.py).

Implementation layers:

1. Board constants are loaded from the canonical TypeScript board definitions in `js/src/constants.ts`, so the Python engine uses the same board graph and position naming as the rest of the project.
2. `Hexchess` models the position state, including board array, side to move, en passant square, clocks, cached king squares, piece lists, and incremental Zobrist hash.
3. Rule logic handles SAN parsing, FEN parsing/stringifying, legal move generation, checks, checkmate, stalemate, promotions, and en passant.
4. Search logic uses negamax with alpha-beta, transposition table lookups, move ordering, killer/history heuristics, and quiescence search.
5. FastAPI exposes `hexchess/evaluate` and `hexchess/ping` using the same `command` / `options` / `response` contract defined by the project engine integration.

## Detailed Engine Characteristics

### Rules and board model

- Uses a 91-cell board array matching the project-wide hexchess coordinate system.
- Loads the board graph and position labels from the shared TypeScript constants instead of duplicating static tables manually.
- Parses and formats the project FEN-like position string used across the repository.
- Supports all standard hexchess piece types already used by the rest of the project: king, queen, rook, bishop, knight, and pawn.
- Generates legal moves, not just pseudo-legal moves, by filtering out moves that leave the side to move in check.
- Supports pawn promotion.
- Supports en passant state and capture handling.
- Detects check, checkmate, and stalemate.

### Position state and performance-oriented internals

- Maintains cached white and black king locations.
- Maintains white and black piece lists so the engine does not need to rescan the full board for every color query.
- Maintains an incremental Zobrist hash for transposition-table lookups.
- Supports reversible move application through `make_move_unsafe()` / `unmake_move()` rather than clone-per-node search.
- Uses direct attack detection helpers for faster legality and tactical checks.

### Search characteristics

- Uses negamax search with alpha-beta pruning.
- Searches from the current legal move list at the root.
- Uses a transposition table keyed by the incremental Zobrist hash.
- Tracks node/evaluation count for reporting back to the UI.
- Applies branch-pruning-oriented move ordering.
- Includes killer move heuristics.
- Includes history heuristics.
- Uses quiescence search to continue through tactical leaf positions instead of stopping immediately at the nominal depth frontier.

### Evaluation characteristics

- Material-based core evaluation.
- Positional advancement bonuses for pawn progress.
- Pawn-attack penalty for pieces left on squares attacked by enemy pawns.
- Tactical stabilization through quiescence search reduces some shallow hanging-piece behavior.
- Terminal outcomes are handled in search rather than only in the static evaluator.

### API characteristics

- Exposed through FastAPI.
- Supports CORS for the local docs Sandbox development origins.
- Preserves the project execute envelope so frontend integrations can use the same payload shape.
- Returns depth, evaluation count, and candidate move list with SAN and score.

### Testing and validation characteristics

- Includes focused Python regression tests in [test_native_engine.py](g:/work/Training/hexchess/pyengine/test_native_engine.py).
- Existing tests currently cover SAN parsing, opening-search sanity, and at least one pawn-attack evaluation regression.
- The engine has also been exercised through the docs Sandbox.

## Notes and Current Caveats

- Some search and evaluation heuristics are still being tuned.
- Exact behavior parity across all project integrations should not be assumed at every position.
- Sandbox-side protections were added so illegal engine output is now rejected instead of silently corrupting the board state.

## API

### POST /execute

Request body follows the project engine message envelope:

```json
{
  "id": "optional-id",
  "command": "hexchess/evaluate",
  "options": {
    "depth": 3,
    "position": "b/qbk/n1b1n/r5r/ppppppppp/11/5P5/4P1P4/3P1B1P3/2P2B2P2/1PRNQBKNRP1 w - 0 1"
  }
}
```

Response shape mirrors engine execute responses:

```json
{
  "id": "optional-id",
  "command": "hexchess/evaluate",
  "options": {
    "depth": 3,
    "position": "..."
  },
  "response": {
    "depth": 3,
    "evaluations": 1234,
    "sans": [
      { "san": "f5f6", "score": 0 }
    ]
  }
}
```

### GET /hexchess/ping

Returns the current timestamp in the same payload wrapper.
