"""empty message

Revision ID: 01904625cb00
Revises: 
Create Date: 2024-08-23 11:15:36.009605

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01904625cb00'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('signature', schema=None) as batch_op:
        batch_op.add_column(sa.Column('signature_date', sa.Date(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('signature', schema=None) as batch_op:
        batch_op.drop_column('signature_date')

    # ### end Alembic commands ###
