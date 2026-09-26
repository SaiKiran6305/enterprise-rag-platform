"""Workspace isolation, users, invitations and conversations.

Revision ID: c6d3a1f705a0
Revises: af1ec69b8625
"""
from alembic import op
from alembic import context
import sqlalchemy as sa

revision = "c6d3a1f705a0"
down_revision = "af1ec69b8625"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("workspaces", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("name", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("users", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_users_workspace_id", "users", ["workspace_id"])
    op.create_unique_constraint("uq_user_workspace_email", "users", ["workspace_id", "email"])
    op.create_table("invitations", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("email", sa.String(255), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False, unique=True), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("used_at", sa.DateTime(timezone=True)))
    op.create_table("conversations", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_conversations_workspace_id", "conversations", ["workspace_id"])
    op.create_table("messages", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("conversation_id", sa.UUID(), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False), sa.Column("position", sa.Integer(), nullable=False), sa.Column("role", sa.String(16), nullable=False), sa.Column("content", sa.Text(), nullable=False), sa.Column("citations", sa.JSON(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.UniqueConstraint("conversation_id", "position", name="uq_message_position"))
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_table("usage_events", sa.Column("id", sa.UUID(), primary_key=True), sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False), sa.Column("operation", sa.String(24), nullable=False), sa.Column("model", sa.String(100), nullable=False), sa.Column("input_tokens", sa.Integer(), nullable=False), sa.Column("output_tokens", sa.Integer(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_usage_events_workspace_id", "usage_events", ["workspace_id"])
    op.add_column("documents", sa.Column("workspace_id", sa.UUID(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True))
    op.add_column("documents", sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True))
    # Existing documents require an explicit owner and cannot silently enter a tenant.
    if not context.is_offline_mode():
        count = op.get_bind().execute(sa.text("SELECT count(*) FROM documents")).scalar_one()
        if count:
            raise RuntimeError("Export or delete existing documents before applying workspace migration")
    op.alter_column("documents", "workspace_id", nullable=False)
    op.alter_column("documents", "owner_id", nullable=False)
    op.create_index("ix_documents_workspace_id", "documents", ["workspace_id"])
    op.drop_constraint("uq_documents_content_hash", "documents", type_="unique")
    op.create_unique_constraint("uq_document_workspace_hash", "documents", ["workspace_id", "content_hash"])


def downgrade():
    raise RuntimeError("Downgrade would discard tenant ownership; restore a database backup")
