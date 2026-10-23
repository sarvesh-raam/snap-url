"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("family_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    op.create_table(
        "links",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("click_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_links_user_id", "links", ["user_id"])

    op.create_table(
        "clicks",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("event_id", sa.String(32), nullable=False, unique=True),
        sa.Column("link_id", sa.BigInteger(), sa.ForeignKey("links.id", ondelete="CASCADE"), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("country", sa.String(2)),
        sa.Column("device", sa.String(16), nullable=False),
        sa.Column("browser", sa.String(64), nullable=False),
        sa.Column("os", sa.String(64), nullable=False),
        sa.Column("referrer", sa.String(255)),
        sa.Column("visitor_hash", sa.String(32), nullable=False),
        sa.Column("is_bot", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_clicks_link_time", "clicks", ["link_id", "clicked_at"])


def downgrade() -> None:
    op.drop_table("clicks")
    op.drop_table("links")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
