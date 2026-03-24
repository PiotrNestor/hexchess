from __future__ import annotations

try:
    from cyengine._native_engine import *  # type: ignore[F403]
except ImportError as exc:
    raise ImportError(
        'cyengine is not built. Run `python -m pip install -e ./cyengine` from the repository root.'
    ) from exc