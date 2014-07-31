"""Added description to usergroup and role

Revision ID: 23b6ea9b0966
Revises: 1290631bd8e1
Create Date: 2014-07-28 21:17:55.662331

"""

# revision identifiers, used by Alembic.
revision = '23b6ea9b0966'
down_revision = '1290631bd8e1'

from alembic import op
import sqlalchemy as sa


INSERTS = """"""
DELETES = """"""


def iter_statements(stmts):
    for st in [x for x in stmts.split('\n') if x]:
        op.execute(st)


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('roles', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('usergroups', sa.Column('description', sa.Text(), nullable=True))
    ### end Alembic commands ###
    iter_statements(INSERTS)


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('usergroups', 'description')
    op.drop_column('roles', 'description')
    ### end Alembic commands ###
    iter_statements(DELETES)