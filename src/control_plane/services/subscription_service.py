from __future__ import annotations

import secrets
from urllib.parse import quote, urlencode

from sqlalchemy.orm import Session

from ..config import settings
from ..models import User
from ..repositories import upsert_subscription


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _build_vless_reality_link(user: User, node_host: str, node_port: int, connect_uuid: str) -> str:
    if not settings.reality_public_key or not settings.reality_short_id:
        raise ValueError("REALITY_PUBLIC_KEY and REALITY_SHORT_ID must be set")

    params = {
        "encryption": "none",
        "security": "reality",
        "sni": settings.reality_server_name,
        "fp": settings.vless_fp,
        "pbk": settings.reality_public_key,
        "sid": settings.reality_short_id,
        "flow": settings.vless_flow,
        "type": "tcp",
    }
    query = urlencode(params)
    tag = quote(f"{user.username}-smart", safe="")
    return f"vless://{connect_uuid}@{node_host}:{node_port}?{query}#{tag}"


def _build_smart_payload(user: User, node_host: str, node_port: int, connect_uuid: str) -> dict:
    link = _build_vless_reality_link(
        user=user,
        node_host=node_host,
        node_port=node_port,
        connect_uuid=connect_uuid,
    )
    return {"profile": "smart", "links": [link]}


def build_or_update_smart_subscription(
    session: Session,
    user: User,
    node_host: str,
    node_port: int,
    connect_uuid: str,
) -> str:
    payload = _build_smart_payload(user=user, node_host=node_host, node_port=node_port, connect_uuid=connect_uuid)
    token = _new_token()
    sub = upsert_subscription(session=session, user=user, token=token, payload=payload, profile="smart")
    return f"{settings.base_subscription_url}/{sub.token}"
