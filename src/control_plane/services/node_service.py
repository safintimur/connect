from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import NodeRole, NodeStatus
from ..repositories import add_audit_event, create_node, get_node_by_name, update_node_status


def register_node(
    session: Session,
    *,
    name: str,
    role: str,
    country: str,
    provider: str,
    provider_node_id: str | None,
    public_ip: str | None,
    actor: str,
) -> str:
    existing = get_node_by_name(session, name)
    if existing:
        raise ValueError(f"Node '{name}' already exists")

    node = create_node(
        session=session,
        name=name,
        role=NodeRole(role),
        country=country,
        provider=provider,
        provider_node_id=provider_node_id,
        public_ip=public_ip,
    )
    add_audit_event(
        session,
        actor=actor,
        action="node.register",
        entity_type="node",
        entity_id=str(node.id),
        metadata={"name": name, "provider_node_id": provider_node_id, "public_ip": public_ip},
    )
    return str(node.id)


def upsert_node(
    session: Session,
    *,
    name: str,
    role: str,
    country: str,
    provider: str,
    provider_node_id: str | None,
    public_ip: str | None,
    actor: str,
) -> str:
    existing = get_node_by_name(session, name)
    if not existing:
        return register_node(
            session,
            name=name,
            role=role,
            country=country,
            provider=provider,
            provider_node_id=provider_node_id,
            public_ip=public_ip,
            actor=actor,
        )

    existing.role = NodeRole(role)
    existing.country = country
    existing.provider = provider
    existing.provider_node_id = provider_node_id
    existing.public_ip = public_ip
    add_audit_event(
        session,
        actor=actor,
        action="node.update",
        entity_type="node",
        entity_id=str(existing.id),
        metadata={"name": name, "provider_node_id": provider_node_id, "public_ip": public_ip},
    )
    return str(existing.id)


def set_node_status(session: Session, name: str, status: str, actor: str) -> None:
    node = get_node_by_name(session, name)
    if not node:
        raise ValueError(f"Node '{name}' not found")

    update_node_status(session, node, NodeStatus(status))
    add_audit_event(
        session,
        actor=actor,
        action="node.status",
        entity_type="node",
        entity_id=str(node.id),
        metadata={"name": name, "status": status},
    )
