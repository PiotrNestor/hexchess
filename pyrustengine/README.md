# pyrustengine

`pyrustengine` is a Python FastAPI wrapper around the existing Rust search engine in [engine](../engine).

It uses a small native Rust FFI bridge in this directory so Python can call the same `hexchess/evaluate` command without going through the browser-only WASM worker.

## Install

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r pyrustengine/requirements.txt
```

Rust and Cargo must also be installed because the wrapper builds the bridge library on first use.

## Run

The wrapper defaults to port `8081`.

Run these commands from the repository root:

```powershell
python -m pyrustengine
```

Equivalent explicit command:

```powershell
python -m uvicorn pyrustengine.main:app --host 127.0.0.1 --port 8081
```

If your current working directory is already [pyrustengine](g:/work/Training/hexchess/pyrustengine), use the local module form instead:

```powershell
python -m uvicorn main:app --host 127.0.0.1 --port 8081
```

You can override the bind port with `PYRUSTENGINE_PORT`.

## API

### `GET /health`

Returns:

```json
{ "status": "ok" }
```

### `GET /hexchess/ping`

Returns the standard engine envelope with a timestamp payload.

### `POST /execute`

Request:

```json
{
  "id": "optional-id",
  "command": "hexchess/evaluate",
  "options": {
    "depth": 2,
    "position": "b/qbk/n1b1n/r5r/ppppppppp/11/5P5/4P1P4/3P1B1P3/2P2B2P2/1PRNQBKNRP1 w - 0 1"
  }
}
```

Supported commands:

- `hexchess/ping`
- `hexchess/evaluate`

## Notes

- The Rust bridge is built from [pyrustengine/Cargo.toml](g:/work/Training/hexchess/pyrustengine/Cargo.toml).
- The bridge will auto-build in release mode if the native library is missing.
- Set `PYRUSTENGINE_LIBRARY` to point at a prebuilt bridge library if you do not want auto-build behavior.
