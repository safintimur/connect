from __future__ import annotations

from sqlalchemy.orm import Session

from ..config import settings
from ..repositories import get_active_clients_for_node


def build_worker_smart_config(session: Session, node, listen_port: int = 443) -> dict:
    if not settings.reality_private_key or not settings.reality_short_id:
        raise ValueError("REALITY_PRIVATE_KEY and REALITY_SHORT_ID must be set")

    clients = []
    for user in get_active_clients_for_node(session, node=node, profile="smart"):
        clients.append({"id": str(user.connect_uuid), "flow": settings.vless_flow})

    return {
        "log": {"loglevel": "warning"},
        "inbounds": [
            {
                "port": listen_port,
                "protocol": "vless",
                "settings": {
                    "clients": clients,
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "reality",
                    "realitySettings": {
                        "show": False,
                        "dest": settings.reality_dest,
                        "xver": 0,
                        "serverNames": [settings.reality_server_name],
                        "privateKey": settings.reality_private_key,
                        "shortIds": [settings.reality_short_id],
                    },
                },
            }
        ],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "blocked", "protocol": "blackhole"},
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {"type": "field", "outboundTag": "direct", "domain": ["geosite:ru"]},
                {"type": "field", "outboundTag": "direct", "ip": ["geoip:ru", "geoip:private"]},
            ],
        },
    }
