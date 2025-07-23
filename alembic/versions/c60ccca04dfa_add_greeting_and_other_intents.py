"""Add greeting and other intents

Revision ID: c60ccca04dfa
Revises: 7242df6a8057
Create Date: 2025-07-23 10:53:18.649585

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c60ccca04dfa'
down_revision = '7242df6a8057'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE intent ADD VALUE IF NOT EXISTS 'GREETING'")
    op.execute("ALTER TYPE intent ADD VALUE IF NOT EXISTS 'OTHER'")

def downgrade():
    pass
    # ### end Alembic commands ###
