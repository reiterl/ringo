"""0.6.2

Revision ID: 1397d9025bd0
Revises: 329d9f86b93b
Create Date: 2013-09-23 23:10:15.224470

"""

# revision identifiers, used by Alembic.
revision = '1397d9025bd0'
down_revision = '329d9f86b93b'

from alembic import op
import sqlalchemy as sa


INSERTS = """"""
DELETES = """"""


def iter_statements(stmts):
    for st in stmts.split('\n'):
        op.execute(st)


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###
    iter_statements(INSERTS)


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    pass
    ### end Alembic commands ###
    iter_statements(DELETES)