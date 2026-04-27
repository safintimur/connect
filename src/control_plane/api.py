from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

from .db import session_scope
from .repositories import get_active_subscription_by_token

app = FastAPI(title="Connect Control API", version="0.1.0")


@app.get("/healthz")
def healthz() -> JSONResponse:
    return JSONResponse({"status": "ok"})


@app.get("/s/{token}")
def subscription(token: str) -> PlainTextResponse:
    with session_scope() as session:
        sub = get_active_subscription_by_token(session, token)
        if not sub:
            raise HTTPException(status_code=404, detail="subscription not found")

        links = sub.payload.get("links", [])
        body = "\n".join(links)
        return PlainTextResponse(body, media_type="text/plain; charset=utf-8")
