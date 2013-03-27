from ringo.model import Base, sqlalchemy as sa
from ringo.model.user import BaseItem
from ringo.model.meta import MetaItem


class ModulItem(BaseItem, Base):
    __tablename__ = 'modules'
    _modul_id = 1
    id = sa.Column(sa.Integer, primary_key=True)
    mid = sa.Column(sa.Integer, sa.ForeignKey('meta.id'))
    name = sa.Column(sa.Text, unique=True, nullable=False)
    label = sa.Column(sa.Text, nullable=False)
    label_plural = sa.Column(sa.Text, nullable=False)
    description = sa.Column(sa.Text)
    str_repr = sa.Column(sa.Text)

    # Relations
    meta = sa.orm.relation("MetaItem", cascade="all, delete-orphan",
                           single_parent=True)
    # Configuration
    _table_fields = [('name', 'Name')]

    def __unicode__(self):
        return self.name


def init_model(dbsession):
    """Will setup the initial model for the usermanagement. This
    includes creating users, usergroups  roles and permissions.

    :dbsession: Database session to which the items will be added.
    :returns: None

    """
    modul = ModulItem(name='modules')
    modul.label = "Modul"
    modul.label_plural = "Modules"
    meta = MetaItem(mid=1, uid=1, gid=None)
    modul.meta = meta
    dbsession.add(modul)
    modul = ModulItem(name='users')
    modul.label = "User"
    modul.label_plural = "Users"
    meta = MetaItem(mid=1, uid=1, gid=None)
    modul.meta = meta
    dbsession.add(modul)
    modul = ModulItem(name='usergroups')
    modul.label = "Usergroup"
    modul.label_plural = "Usergroups"
    meta = MetaItem(mid=1, uid=1, gid=None)
    modul.meta = meta
    dbsession.add(modul)
    modul = ModulItem(name='roles')
    modul.label = "Role"
    modul.label_plural = "Roles"
    meta = MetaItem(mid=1, uid=1, gid=None)
    modul.meta = meta
    dbsession.add(modul)
    modul = ModulItem(name='permissions')
    modul.label = "Permission"
    modul.label_plural = "Permissions"
    meta = MetaItem(mid=1, uid=1, gid=None)
    modul.meta = meta
    dbsession.add(modul)
