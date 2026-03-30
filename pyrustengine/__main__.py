from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.getenv("PYRUSTENGINE_HOST", "127.0.0.1")
    port = int(os.getenv("PYRUSTENGINE_PORT", "8081"))
    reload_enabled = os.getenv("PYRUSTENGINE_RELOAD", "false").lower() in {"1", "true", "yes", "on"}

    uvicorn.run("pyrustengine.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    main()
