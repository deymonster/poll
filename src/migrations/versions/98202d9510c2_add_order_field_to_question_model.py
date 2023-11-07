"""Add 'order' field to Question model

Revision ID: 98202d9510c2
Revises: 41bb4101d876
Create Date: 2023-11-06 12:07:50.969616

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98202d9510c2'
down_revision = '41bb4101d876'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('question', sa.Column('order', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_question_order'), 'question', ['order'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_question_order'), table_name='question')
    op.drop_column('question', 'order')
    # ### end Alembic commands ###
