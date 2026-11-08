"""movie keywords, poster palette and tmdb id

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-07 13:10:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("keywords", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("movies", sa.Column("art_palette", sa.JSON(), nullable=False, server_default="[]"))
    op.add_column("movies", sa.Column("tmdb_id", sa.Integer(), nullable=True))
    op.create_unique_constraint(op.f("uq_movies_tmdb_id"), "movies", ["tmdb_id"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_movies_tmdb_id"), "movies", type_="unique")
    op.drop_column("movies", "tmdb_id")
    op.drop_column("movies", "art_palette")
    op.drop_column("movies", "keywords")
