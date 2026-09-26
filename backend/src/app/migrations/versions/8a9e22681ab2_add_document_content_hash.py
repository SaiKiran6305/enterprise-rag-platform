"""add document content hash

Revision ID: 8a9e22681ab2
Revises: 8bcd8ced50c8
Create Date: 2026-09-13 16:22:23.469396
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8a9e22681ab2"

down_revision: Union[
    str,
    Sequence[str],
    None,
] = "8bcd8ced50c8"

branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None

depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    """Add content hash to documents."""
    op.add_column(
        "documents",
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_documents_content_hash",
        "documents",
        ["content_hash"],
    )


def downgrade() -> None:
    """Remove content hash from documents."""
    op.drop_constraint(
        "uq_documents_content_hash",
        "documents",
        type_="unique",
    )

    op.drop_column(
        "documents",
        "content_hash",
    )