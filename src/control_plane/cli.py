from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timezone

import typer
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from .db import session_scope
from .models import AssignmentStatus, NodeAssignment
from .providers.do_provider import DOProvider, DropletSpec
from .repositories import add_audit_event, assign_user_to_node, get_node_by_name, get_user_by_username
from .services.node_service import register_node, set_node_status, upsert_node
from .services.subscription_service import build_or_update_smart_subscription
from .services.user_service import create_user_with_identity, disable_user_by_username
from .services.xray_service import build_worker_smart_config

app = typer.Typer(help="Connect control-plane CLI")


@app.command("init-db")
def init_db() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    typer.echo("Database migration complete (alembic head)")


@app.command("user-add")
def user_add(
    username: str,
    display_name: str,
    actor: str = typer.Option("admin", help="Audit actor name"),
) -> None:
    with session_scope() as session:
        user = create_user_with_identity(session, username=username, display_name=display_name, actor=actor)
    typer.echo(f"User created: {user.username} ({user.id})")
    typer.echo(f"Connect UUID: {user.connect_uuid}")


@app.command("user-disable")
def user_disable(username: str, actor: str = typer.Option("admin")) -> None:
    with session_scope() as session:
        user = disable_user_by_username(session, username=username, actor=actor)
    typer.echo(f"User disabled: {user.username}")


@app.command("user-delete")
def user_delete(username: str, actor: str = typer.Option("admin")) -> None:
    with session_scope() as session:
        user = get_user_by_username(session, username)
        if not user:
            raise typer.BadParameter(f"User '{username}' not found")
        user_id = str(user.id)
        session.delete(user)
        add_audit_event(
            session,
            actor=actor,
            action="user.delete",
            entity_type="user",
            entity_id=user_id,
            metadata={"username": username},
        )
    typer.echo(f"User deleted: {username}")


@app.command("node-register")
def node_register(
    name: str,
    role: str = typer.Option("worker"),
    country: str = typer.Option("gb"),
    provider: str = typer.Option("digitalocean"),
    provider_node_id: str = typer.Option("", help="Provider native node id"),
    public_ip: str = typer.Option("", help="Public IP of node"),
    actor: str = typer.Option("admin"),
) -> None:
    with session_scope() as session:
        node_id = register_node(
            session,
            name=name,
            role=role,
            country=country,
            provider=provider,
            provider_node_id=provider_node_id or None,
            public_ip=public_ip or None,
            actor=actor,
        )
    typer.echo(f"Node registered: {name} ({node_id})")


@app.command("node-status")
def node_status(name: str, status: str, actor: str = typer.Option("admin")) -> None:
    with session_scope() as session:
        set_node_status(session, name=name, status=status, actor=actor)
    typer.echo(f"Node status updated: {name} -> {status}")


@app.command("node-info")
def node_info(name: str) -> None:
    with session_scope() as session:
        node = get_node_by_name(session, name)
        if not node:
            raise typer.BadParameter(f"Node '{name}' not found")
        payload = {
            "name": node.name,
            "role": node.role.value,
            "status": node.status.value,
            "country": node.country,
            "provider": node.provider,
            "provider_node_id": node.provider_node_id,
            "public_ip": node.public_ip,
        }
    typer.echo(json.dumps(payload, ensure_ascii=True))


@app.command("node-upsert")
def node_upsert(
    name: str,
    role: str = typer.Option("worker"),
    country: str = typer.Option("gb"),
    provider: str = typer.Option("digitalocean"),
    provider_node_id: str = typer.Option("", help="Provider native node id"),
    public_ip: str = typer.Option("", help="Public IP of node"),
    actor: str = typer.Option("automation"),
) -> None:
    with session_scope() as session:
        node_id = upsert_node(
            session,
            name=name,
            role=role,
            country=country,
            provider=provider,
            provider_node_id=provider_node_id or None,
            public_ip=public_ip or None,
            actor=actor,
        )
    typer.echo(f"Node upserted: {name} ({node_id})")


@app.command("subscription-build")
def subscription_build(
    username: str,
    node_name: str,
    node_port: int = typer.Option(443),
    actor: str = typer.Option("admin"),
) -> None:
    with session_scope() as session:
        user = get_user_by_username(session, username)
        if not user:
            raise typer.BadParameter(f"User '{username}' not found")

        node = get_node_by_name(session, node_name)
        if not node or not node.public_ip:
            raise typer.BadParameter(f"Node '{node_name}' not found or has no public_ip")

        assign_user_to_node(session, user=user, node=node, profile="smart")
        sub_url = build_or_update_smart_subscription(
            session,
            user=user,
            node_host=node.public_ip,
            node_port=node_port,
            connect_uuid=str(user.connect_uuid),
        )
        add_audit_event(
            session,
            actor=actor,
            action="subscription.build",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"node": node_name, "profile": "smart"},
        )
    typer.echo(f"Subscription URL: {sub_url}")


@app.command("user-provision-smart")
def user_provision_smart(
    username: str,
    display_name: str,
    node_name: str,
    node_port: int = typer.Option(443),
    actor: str = typer.Option("admin"),
) -> None:
    with session_scope() as session:
        user = get_user_by_username(session, username)
        if not user:
            user = create_user_with_identity(session, username=username, display_name=display_name, actor=actor)

        node = get_node_by_name(session, node_name)
        if not node or not node.public_ip:
            raise typer.BadParameter(f"Node '{node_name}' not found or has no public_ip")

        assign_user_to_node(session, user=user, node=node, profile="smart")
        sub_url = build_or_update_smart_subscription(
            session,
            user=user,
            node_host=node.public_ip,
            node_port=node_port,
            connect_uuid=str(user.connect_uuid),
        )
        add_audit_event(
            session,
            actor=actor,
            action="user.provision.smart",
            entity_type="user",
            entity_id=str(user.id),
            metadata={"username": username, "node": node_name},
        )

    typer.echo(f"Provisioned user: {username}")
    typer.echo(f"Subscription URL: {sub_url}")


@app.command("do-create-worker")
def do_create_worker(
    name: str,
    region: str = typer.Option("", help="DigitalOcean region, e.g. lon1"),
    size: str = typer.Option("", help="Droplet size"),
    image: str = typer.Option("", help="Droplet image slug"),
) -> None:
    provider = DOProvider()
    droplet = provider.create_worker_droplet(
        DropletSpec(
            name=name,
            region=region or None,
            size=size or None,
            image=image or None,
            tags=["connect", "worker", "uk"],
        )
    )
    typer.echo(json.dumps(droplet, ensure_ascii=True))


@app.command("do-get-worker")
def do_get_worker(droplet_id: int) -> None:
    provider = DOProvider()
    payload = provider.get_droplet(droplet_id=droplet_id)
    typer.echo(json.dumps(payload, ensure_ascii=True))


@app.command("do-delete-worker")
def do_delete_worker(droplet_id: int) -> None:
    provider = DOProvider()
    payload = provider.delete_droplet(droplet_id=droplet_id)
    typer.echo(json.dumps(payload, ensure_ascii=True))


@app.command("xray-render-node-config")
def xray_render_node_config(
    node_name: str,
    output: str = typer.Option("", help="Output file path"),
    listen_port: int = typer.Option(443),
) -> None:
    with session_scope() as session:
        node = get_node_by_name(session, node_name)
        if not node:
            raise typer.BadParameter(f"Node '{node_name}' not found")

        config = build_worker_smart_config(session=session, node=node, listen_port=listen_port)

    rendered = json.dumps(config, ensure_ascii=True, indent=2)
    if output:
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
        typer.echo(f"Rendered config: {out_path}")
        return

    typer.echo(rendered)


@app.command("worker-cutover-smart")
def worker_cutover_smart(
    old_node_name: str,
    new_node_name: str,
    node_port: int = typer.Option(443),
    actor: str = typer.Option("automation"),
) -> None:
    moved = 0
    with session_scope() as session:
        old_node = get_node_by_name(session, old_node_name)
        if not old_node:
            raise typer.BadParameter(f"Old node '{old_node_name}' not found")
        new_node = get_node_by_name(session, new_node_name)
        if not new_node or not new_node.public_ip:
            raise typer.BadParameter(f"New node '{new_node_name}' not found or has no public_ip")

        assignments = list(
            session.scalars(
                select(NodeAssignment).where(
                    NodeAssignment.node_id == old_node.id,
                    NodeAssignment.profile == "smart",
                    NodeAssignment.status == AssignmentStatus.active,
                )
            )
        )

        for old in assignments:
            old.status = AssignmentStatus.inactive
            old.unassigned_at = datetime.now(timezone.utc)

            user = old.user
            assign_user_to_node(session, user=user, node=new_node, profile="smart")
            build_or_update_smart_subscription(
                session=session,
                user=user,
                node_host=new_node.public_ip,
                node_port=node_port,
                connect_uuid=str(user.connect_uuid),
            )
            moved += 1

        add_audit_event(
            session,
            actor=actor,
            action="worker.cutover.smart",
            entity_type="node",
            entity_id=str(new_node.id),
            metadata={"old_node": old_node_name, "new_node": new_node_name, "moved_users": moved},
        )

    typer.echo(f"Cutover complete: moved {moved} user(s) {old_node_name} -> {new_node_name}")


if __name__ == "__main__":
    app()
