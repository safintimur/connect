from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import (
    AssignmentStatus,
    AuditEvent,
    Node,
    NodeAssignment,
    NodeRole,
    NodeStatus,
    Subscription,
    User,
    UserStatus,
)


def create_user(session: Session, username: str, display_name: str) -> User:
    user = User(username=username, display_name=display_name)
    session.add(user)
    session.flush()
    return user


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def disable_user(session: Session, user: User) -> None:
    user.status = UserStatus.disabled
    user.disabled_at = datetime.now(timezone.utc)


def create_node(
    session: Session,
    name: str,
    role: NodeRole,
    country: str,
    provider: str,
    provider_node_id: str | None,
    public_ip: str | None,
    capabilities: dict | None = None,
) -> Node:
    node = Node(
        name=name,
        role=role,
        country=country,
        provider=provider,
        provider_node_id=provider_node_id,
        public_ip=public_ip,
        capabilities=capabilities or {},
        status=NodeStatus.active,
    )
    session.add(node)
    session.flush()
    return node


def get_node_by_name(session: Session, name: str) -> Node | None:
    return session.scalar(select(Node).where(Node.name == name))


def update_node_status(session: Session, node: Node, status: NodeStatus) -> None:
    node.status = status


def assign_user_to_node(session: Session, user: User, node: Node, profile: str = "smart") -> NodeAssignment:
    existing = session.scalar(
        select(NodeAssignment).where(
            NodeAssignment.user_id == user.id,
            NodeAssignment.profile == profile,
            NodeAssignment.status == AssignmentStatus.active,
        )
    )
    if existing:
        return existing

    assignment = NodeAssignment(user_id=user.id, node_id=node.id, profile=profile, status=AssignmentStatus.active)
    session.add(assignment)
    session.flush()
    return assignment


def get_active_assignments_for_node(session: Session, node: Node, profile: str = "smart") -> list[NodeAssignment]:
    rows = session.scalars(
        select(NodeAssignment).where(
            NodeAssignment.node_id == node.id,
            NodeAssignment.profile == profile,
            NodeAssignment.status == AssignmentStatus.active,
        )
    )
    return list(rows)


def upsert_subscription(
    session: Session,
    user: User,
    token: str,
    payload: dict,
    profile: str = "smart",
) -> Subscription:
    existing = session.scalar(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.profile == profile,
            Subscription.is_active.is_(True),
        )
    )
    if existing:
        existing.config_version += 1
        existing.payload = payload
        return existing

    sub = Subscription(user_id=user.id, token=token, payload=payload, profile=profile)
    session.add(sub)
    session.flush()
    return sub


def get_active_subscription_by_token(session: Session, token: str) -> Subscription | None:
    return session.scalar(
        select(Subscription).where(
            Subscription.token == token,
            Subscription.is_active.is_(True),
        )
    )


def get_active_clients_for_node(session: Session, node: Node, profile: str = "smart") -> list[User]:
    rows = session.scalars(
        select(User)
        .join(NodeAssignment, NodeAssignment.user_id == User.id)
        .where(
            NodeAssignment.node_id == node.id,
            NodeAssignment.profile == profile,
            NodeAssignment.status == AssignmentStatus.active,
            User.status == UserStatus.active,
        )
    )
    return list(rows)


def add_audit_event(
    session: Session,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        audit_metadata=metadata or {},
    )
    session.add(event)
    session.flush()
    return event
