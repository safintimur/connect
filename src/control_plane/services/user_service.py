from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import User
from ..repositories import add_audit_event, create_user, disable_user, get_user_by_username


def create_user_with_identity(session: Session, username: str, display_name: str, actor: str) -> User:
    existing = get_user_by_username(session, username)
    if existing:
        raise ValueError(f"User '{username}' already exists")

    user = create_user(session, username=username, display_name=display_name)
    add_audit_event(
        session,
        actor=actor,
        action="user.create",
        entity_type="user",
        entity_id=str(user.id),
        metadata={"username": username, "connect_uuid": str(user.connect_uuid)},
    )
    return user


def disable_user_by_username(session: Session, username: str, actor: str) -> User:
    user = get_user_by_username(session, username)
    if not user:
        raise ValueError(f"User '{username}' not found")

    disable_user(session, user)
    add_audit_event(
        session,
        actor=actor,
        action="user.disable",
        entity_type="user",
        entity_id=str(user.id),
        metadata={"username": username},
    )
    return user
