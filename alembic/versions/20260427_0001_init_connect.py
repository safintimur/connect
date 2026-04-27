"""init connect schema

Revision ID: 20260427_0001
Revises: None
Create Date: 2026-04-27 13:45:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260427_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    user_status = sa.Enum("active", "disabled", name="user_status")
    node_role = sa.Enum("control", "worker", name="node_role")
    node_status = sa.Enum("provisioning", "active", "degraded", "draining", "disabled", name="node_status")
    assignment_status = sa.Enum("active", "inactive", name="assignment_status")

    bind = op.get_bind()
    user_status.create(bind, checkfirst=True)
    node_role.create(bind, checkfirst=True)
    node_status.create(bind, checkfirst=True)
    assignment_status.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("connect_uuid", postgresql.UUID(as_uuid=True), nullable=False, unique=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("status", user_status, nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "nodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("role", node_role, nullable=False),
        sa.Column("country", sa.String(length=8), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="digitalocean"),
        sa.Column("provider_node_id", sa.String(length=64), nullable=True),
        sa.Column("public_ip", sa.String(length=64), nullable=True),
        sa.Column("status", node_status, nullable=False, server_default="provisioning"),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )

    op.create_table(
        "node_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("profile", sa.String(length=32), nullable=False, server_default="smart"),
        sa.Column("status", assignment_status, nullable=False, server_default="active"),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_user_profile_active_assignment",
        "node_assignments",
        ["user_id", "profile"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index("idx_assignments_node_status", "node_assignments", ["node_id", "status"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(length=96), nullable=False, unique=True),
        sa.Column("profile", sa.String(length=32), nullable=False, server_default="smart"),
        sa.Column("config_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_subscriptions_user_active", "subscriptions", ["user_id", "is_active"], unique=False)

    op.create_table(
        "audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("idx_audit_created_at", "audit_events", ["created_at"], unique=False)

    op.create_index("idx_nodes_status", "nodes", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_nodes_status", table_name="nodes")
    op.drop_index("idx_audit_created_at", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("idx_subscriptions_user_active", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("idx_assignments_node_status", table_name="node_assignments")
    op.drop_index("uq_user_profile_active_assignment", table_name="node_assignments")
    op.drop_table("node_assignments")
    op.drop_table("nodes")
    op.drop_table("users")

    assignment_status = sa.Enum("active", "inactive", name="assignment_status")
    node_status = sa.Enum("provisioning", "active", "degraded", "draining", "disabled", name="node_status")
    node_role = sa.Enum("control", "worker", name="node_role")
    user_status = sa.Enum("active", "disabled", name="user_status")

    bind = op.get_bind()
    assignment_status.drop(bind, checkfirst=True)
    node_status.drop(bind, checkfirst=True)
    node_role.drop(bind, checkfirst=True)
    user_status.drop(bind, checkfirst=True)
