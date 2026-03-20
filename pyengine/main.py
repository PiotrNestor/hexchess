from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field


ROOT_DIR = Path(__file__).resolve().parent.parent
BRIDGE_PATH = Path(__file__).resolve().parent / "engine_bridge.mjs"


class EngineError(BaseModel):
    message: str


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    command: str
    options: dict[str, Any] = Field(default_factory=dict)
    id: str | None = None


class ExecuteResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    command: str
    options: dict[str, Any]
    response: dict[str, Any]
    id: str | None = None


class ExecuteFailure(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)
    error: EngineError


app = FastAPI(title="hexchess pyengine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def run_bridge(payload: ExecuteRequest) -> dict[str, Any]:
    node_executable = shutil.which("node")

    if not node_executable:
        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to start bridge: 'node' executable was not found in PATH. "
                "Ensure Node.js is installed and available in the environment running uvicorn."
            ),
        )

    def run_node_bridge() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [node_executable, str(BRIDGE_PATH)],
            input=json.dumps(payload.model_dump()),
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
            check=False,
            env=os.environ.copy(),
        )

    try:
        process = await asyncio.to_thread(run_node_bridge)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to execute bridge process: {exc}",
        ) from exc

    output = process.stdout.strip()
    err_output = process.stderr.strip()

    if not output:
        raise HTTPException(status_code=500, detail=f"pyengine bridge returned empty output: {err_output}")

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"pyengine bridge returned invalid JSON: {output}") from exc

    if process.returncode != 0:
        message = (
            data.get("error", {}).get("message")
            if isinstance(data, dict)
            else None
        ) or err_output or "Unknown pyengine bridge error"
        raise HTTPException(status_code=500, detail=message)

    return data


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(payload: ExecuteRequest) -> ExecuteResponse:
    data = await run_bridge(payload)

    if "error" in data:
        error = ExecuteFailure(
            id=payload.id,
            options=payload.options,
            error=EngineError(message=str(data["error"].get("message", "Unknown engine error"))),
        )
        raise HTTPException(status_code=400, detail=error.model_dump())

    return ExecuteResponse(
        id=payload.id,
        command=str(data.get("command", payload.command)),
        options=dict(data.get("options", payload.options)),
        response=dict(data.get("response", {})),
    )


@app.get("/hexchess/ping")
async def ping() -> ExecuteResponse:
    payload = ExecuteRequest(command="hexchess/ping", options={})
    data = await run_bridge(payload)
    return ExecuteResponse(
        command="hexchess/ping",
        options={},
        response=dict(data.get("response", {})),
    )
