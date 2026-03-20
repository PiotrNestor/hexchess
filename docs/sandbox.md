---
layout: doc
---

# Sandbox

Clear positions with `Delete` or `Backspace`, and input pieces by their FEN character.

Use the `Engine` selector above the board to choose between:

- `Rust (WASM Worker)` (default, browser worker)
- `Python (FastAPI)` (local API server)

To use the Python engine, run:

```sh
python -m venv .venv
.venv/Scripts/activate
pip install -r pyengine/requirements.txt
uvicorn pyengine.main:app --reload --host 127.0.0.1 --port 8000
```

<ClientOnly>
	<Sandbox />
</ClientOnly>

<script setup>
import Sandbox from './sandbox/Sandbox.vue'
</script>