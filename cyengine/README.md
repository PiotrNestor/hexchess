# cyengine

`cyengine` is the Cython build of the hexchess Python engine.

It is based directly on the current `pyengine` search, move-generation, evaluation, and API code, but packages the engine core as a compiled extension module so it can be optimized further without changing the public engine contract.

## Current Status

The first `cyengine` version is intentionally conservative:

- the engine logic mirrors `pyengine`
- the public API remains the same
- the main difference is packaging the core engine as `cyengine._native_engine`

This means `cyengine` is a compiled sibling of `pyengine`, not a new engine design.

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r cyengine/requirements.txt
pip install -e ./cyengine
```

## Run

```bash
uvicorn cyengine.main:app --reload --host 127.0.0.1 --port 8001
```

## Implementation Summary

- The compiled engine source lives in `_native_engine.pyx`.
- `native_engine.py` is the stable import shim for application code.
- `main.py` exposes the same FastAPI `command` / `options` / `response` engine contract used elsewhere in the project.
- `test_native_engine.py` reuses the existing Python-engine regression coverage against the compiled module.

## Build Notes

- Build the extension with `pip install -e ./cyengine` from the repository root.
- The editable install compiles `cyengine._native_engine` in place.
- If the extension has not been built yet, importing `cyengine.native_engine` raises a clear error that tells you how to build it.
- Benchmark with `python cyengine/benchmark.py --depths 3 4 --repeat 3` to compare the compiled engine against the shared benchmark corpus in `pyengine/benchmarks.yaml`.
- Compare both engines directly with `python cyengine/compare_benchmark.py --depths 3 4 --repeat 3`.

## Caveats

- This first Cython version is a packaging and compilation step, not a full type-annotated Cython rewrite.
- Real performance gains will depend on follow-up work: replacing Python containers in hot paths, adding Cython `cdef` data paths, and specializing inner loops.
- The current goal is to provide a compiled foundation that stays behaviorally aligned with `pyengine`.
