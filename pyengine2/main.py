from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from pyengine2.native_engine import NativeEngineError, execute_command
from pyengine2.version import PYENGINE2_VERSION


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


app = FastAPI(title="hexchess pyengine2", version=PYENGINE2_VERSION)

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/execute", response_model=ExecuteResponse)
async def execute(payload: ExecuteRequest) -> ExecuteResponse:
    try:
        response = execute_command(payload.command, payload.options)
    except NativeEngineError as exc:
        error = ExecuteFailure(
            id=payload.id,
            options=payload.options,
            error=EngineError(message=str(exc)),
        )
        raise HTTPException(status_code=400, detail=error.model_dump()) from exc

    return ExecuteResponse(
        id=payload.id,
        command=payload.command,
        options=payload.options,
        response=response,
    )


@app.get("/hexchess/ping")
async def ping() -> ExecuteResponse:
    response = execute_command("hexchess/ping", {})
    return ExecuteResponse(
        command="hexchess/ping",
        options={},
        response=response,
    )