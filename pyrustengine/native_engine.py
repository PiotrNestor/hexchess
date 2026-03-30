from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path
from threading import Lock
from typing import Any


class NativeEngineError(ValueError):
    pass


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = PACKAGE_DIR.parent
LIBRARY_ENV_VAR = "PYRUSTENGINE_LIBRARY"
_LIBRARY_LOCK = Lock()
_LIBRARY_HANDLE: ctypes.CDLL | None = None


def error(message: str) -> None:
    raise NativeEngineError(f"[hexchess error] {message}")


def execute_command(command: str, options: dict[str, Any] | None = None) -> dict[str, Any]:
    library = _load_library()
    command_bytes = command.encode("utf-8")
    options_bytes = json.dumps(options or {}, separators=(",", ":")).encode("utf-8")
    payload_ptr = library.hexchess_engine_execute(command_bytes, options_bytes)

    if not payload_ptr:
        error("rust engine returned an empty response")

    try:
        payload_raw = ctypes.string_at(payload_ptr).decode("utf-8")
    finally:
        library.hexchess_engine_string_free(payload_ptr)

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        error(f"failed to decode rust engine response: {exc}")

    if not payload.get("ok"):
        message = payload.get("error", {}).get("message", "unknown engine error")
        error(str(message))

    response = payload.get("response")
    if not isinstance(response, dict):
        error("rust engine returned an invalid response payload")

    return response


def _load_library() -> ctypes.CDLL:
    global _LIBRARY_HANDLE

    if _LIBRARY_HANDLE is not None:
        return _LIBRARY_HANDLE

    with _LIBRARY_LOCK:
        if _LIBRARY_HANDLE is not None:
            return _LIBRARY_HANDLE

        library_path = _resolve_library_path()
        handle = ctypes.CDLL(str(library_path))
        handle.hexchess_engine_execute.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        handle.hexchess_engine_execute.restype = ctypes.c_void_p
        handle.hexchess_engine_string_free.argtypes = [ctypes.c_void_p]
        handle.hexchess_engine_string_free.restype = None
        _LIBRARY_HANDLE = handle

    return _LIBRARY_HANDLE


def _resolve_library_path() -> Path:
    override = os.getenv(LIBRARY_ENV_VAR)
    if override:
        library_path = Path(override).expanduser().resolve()
        if not library_path.exists():
            error(f"configured rust engine library does not exist: {library_path}")
        return library_path

    candidates = _library_candidates()
    for candidate in candidates:
        if candidate.exists():
            return candidate

    _build_library()

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched_paths = ", ".join(str(path) for path in candidates)
    error(f"rust engine library was not found after build. searched: {searched_paths}")
    raise AssertionError("unreachable")


def _build_library() -> None:
    command = ["cargo", "build", "--release", "--manifest-path", str(PACKAGE_DIR / "Cargo.toml")]

    try:
        subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        error("cargo is required to build the Rust bridge, but it was not found on PATH")
        raise exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        details = stderr or stdout or str(exc)
        error(f"failed to build Rust bridge: {details}")


def _library_candidates() -> list[Path]:
    library_name = _library_filename()
    return [
        PACKAGE_DIR / "target" / "release" / library_name,
        PACKAGE_DIR / "target" / "debug" / library_name,
    ]


def _library_filename() -> str:
    if sys.platform == "win32":
        return "hexchess_pyrustengine.dll"
    if sys.platform == "darwin":
        return "libhexchess_pyrustengine.dylib"
    return "libhexchess_pyrustengine.so"
