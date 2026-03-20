# pyengine

Python API wrapper for the existing hexchess Rust/WASM engine.

## Install

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r pyengine/requirements.txt
```

## Run

```bash
uvicorn pyengine.main:app --reload --host 127.0.0.1 --port 8000
```

## API

### POST /execute

Request body mirrors worker messages:

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

Returns current timestamp in the same payload wrapper.
