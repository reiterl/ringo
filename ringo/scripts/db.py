import logging
import shutil
import os
import time
from sqlalchemy import engine_from_config
import transaction

from alembic.config import Config
from alembic import command
from pyramid.paster import (
    get_appsettings,
    setup_logging,
)
from ringo.lib.sql import DBSession
from ringo.lib.helpers import get_app_location, dynamic_import
from ringo.lib.imexport import JSONExporter, JSONImporter
from ringo.model.modul import ModulItem

log = logging.getLogger(__name__)

def is_locked(filepath):
    """Checks if a file is locked by opening it in append mode.
    If no exception thrown, then the file is not locked.
    """
    locked = None
    file_object = None
    if os.path.exists(filepath):
        try:
            #print "Trying to open %s." % filepath
            buffer_size = 8
            # Opening file in append mode and read the first 8 characters.
            file_object = open(filepath, 'a', buffer_size)
            if file_object:
                #print "%s is not locked." % filepath
                locked = False
        except IOError, message:
            print "File is locked (unable to open in append mode). %s." % \
                  message
            locked = True
        finally:
            if file_object:
                file_object.close()
                #print "%s closed." % filepath
    else:
        print "%s not found." % filepath
    return locked


def get_last_revision_file(args):
    """Will return the name of the latest revision file of the application"""
    script_path = []
    script_path.append(get_app_location(args.app))
    script_path.append(args.app)
    script_path.append("alembic")
    script_path.append("versions")
    cwd = os.getcwd()
    os.chdir(os.path.join(*script_path))
    script_path.append(max([fn for fn in os.listdir(".") if fn.endswith("py")],
                       key=os.path.getctime))
    os.chdir(cwd)
    return os.path.join(*script_path)


def get_session(config_file):
    """Will return a database session based on the application
    configuration"""
    setup_logging(config_file)
    settings = get_appsettings(config_file)
    engine = engine_from_config(settings, 'sqlalchemy.')
    DBSession.configure(bind=engine)
    return DBSession


def copy_initial_migration_scripts(args):
    """Will copy the initial db migration scripts into the alembic
    versions folder of the application.
    """
    dst_path = []
    dst_path.append(get_app_location(args.app))
    dst_path.append(args.app)
    dst_path.append("alembic")
    dst_path.append("versions")
    src_path = []
    src_path.append(get_app_location(args.base))
    src_path.append(args.base)
    src_path.append("alembic")
    src_path.append("versions")

    src = os.path.join(*src_path)
    dst = os.path.join(*dst_path)
    dst_files = os.listdir(dst)
    src_files = os.listdir(src)
    # Only copy the initial files if the directory is empty.
    if len(dst_files) >= 1:
        return
    for file_name in src_files:
        full_file_name = os.path.join(src, file_name)
        if (os.path.isfile(full_file_name)):
            shutil.copy(full_file_name, dst)


def create_new_revision(args, msg=None):
    """Will create a new autogenerated revision file. An returns the
    path of the new generated file."""
    cfg = get_alembic_config(args)
    command.revision(cfg, message=msg, autogenerate=True)
    revision_file = get_last_revision_file(args)
    while is_locked(revision_file):
        time.sleep(1)
    return revision_file


def replace_insert_stmt(revision_file, sql):
    """Will replace the empty INSERT statement in the given revison file
    with the given sql statements."""
    with open(revision_file, "r") as f:
        data = f.read()
    time.sleep(2)
    with open(revision_file, "w") as f:
        f.write(data.replace('INSERTS = """"""',
                              'INSERTS = """%s"""' % "\n".join(sql)))

def get_alembic_config(args, app=None):
    """Return a alembic configuration

    :app: Name of the application
    :returns: Alembic configuration

    """

    config_path = []
    config_path.append(get_app_location(args.app))
    config_path.append("alembic.ini")
    cfg = Config(os.path.join(*config_path))
    if args.config:
        app_config = get_appsettings(args.config)
        cfg.set_main_option("sqlalchemy.url",
                            app_config.get('sqlalchemy.url'))
    return cfg


def handle_db_init_command(args):
    copy_initial_migration_scripts(args)
    handle_db_upgrade_command(args)


def handle_db_upgrade_command(args):
    cfg = get_alembic_config(args)
    command.upgrade(cfg, "head")

def handle_db_revision_command(args):
    path = create_new_revision(args)
    print "New migration script created: %s" % path

def handle_db_savedata_command(args):
    path = []
    path.append(get_app_location(args.app))
    path.append(args.config)
    session = get_session(os.path.join(*path))
    modul_clazzpath = session.query(ModulItem).filter(ModulItem.name == args.modul).all()[0].clazzpath
    modul = dynamic_import(modul_clazzpath)
    exporter = JSONExporter(modul, serialized=False,
                            relations=args.include_relations)
    print exporter.perform(session.query(modul).all())

def handle_db_loaddata_command(args):
    path = []
    path.append(get_app_location(args.app))
    path.append(args.config)
    session = get_session(os.path.join(*path))
    modul_clazzpath = session.query(ModulItem).filter(ModulItem.name == args.modul).all()[0].clazzpath
    modul = dynamic_import(modul_clazzpath)
    importer = JSONImporter(modul, session)
    items = []
    updated = 0
    created = 0
    with open(args.fixture) as f:
        items = importer.perform(f.read(), use_uuid=(not args.loadbyid))
        for item, action in items:
            # Add all new items to the session
            if action.find("CREATE") > -1:
                session.add(item)
                created += 1
            else:
                updated += 1
        try:
            transaction.commit()
            print "Updated %s items, Created %s items" % (updated, created)
        except Exception as e:
            print str(e)
            print "Loading data failed!"

def handle_db_uuid_command(args):
    path = []
    path.append(get_app_location(args.app))
    path.append(args.config)
    session = get_session(os.path.join(*path))
    modul_clazzpath = session.query(ModulItem).filter(ModulItem.name == args.modul).all()[0].clazzpath
    modul = dynamic_import(modul_clazzpath)
    updated = 0
    created = 0
    for item in session.query(modul).all():
        if item.uuid:
            if args.missing_only:
                continue
            else:
                item.reset_uuid()
                updated += 1
        else:
            item.reset_uuid()
            created += 1
    try:
        transaction.commit()
        print "Updated %s items, Created %s items" % (updated, created)
    except:
        print "Loading data failed!"

def _get_user_id_function():
    out = []
    out.append("CREATE OR REPLACE FUNCTION uid() RETURNS integer")
    out.append("LANGUAGE 'plpgsql' STABLE")
    out.append("AS $$")
    out.append("  DECLARE")
    out.append("  uid integer;")
    out.append("  BEGIN")
    out.append("    SELECT INTO uid id FROM users WHERE login = session_user;")
    out.append("    RETURN uid;")
    out.append("  END;")
    out.append("$$;")
    return "\n".join(out)


def handle_db_restrict_command(args):
    """Will return a SQL statement to restrict the access to the given
    tables by revoking all priviledges to the table in the public
    scheme. Instead of this a view with the same name as the table in
    the restricted view will be defined which only returns datasets
    which the current user owns or is member of the items group."""
    out = []
    out.append("-- Execute this as user postgres")
    out.append("CREATE SCHEMA IF NOT EXISTS restriced;")
    out.append(_get_user_id_function())
    out.append("REVOKE ALL ON TABLE public.%ss FROM PUBLIC;" % args.modul)
    out.append("CREATE OR REPLACE VIEW %ss AS " % args.modul)
    out.append("SELECT * FROM public.%ss WHERE " % args.modul)
    out.append("uid = uid()")
    out.append("OR gid IN ( SELECT gid from nm_user_usergroups where uid = uid() ) ")
    out.append("OR uid() IN ( select uid from nm_user_roles where rid = 1 );")
    out.append("GRANT ALL ON TABLE restricted.%ss TO PUBLIC;" % args.modul)
    out.append("-- Do not to forget to change the default searchpath to '$user', restricted, public")
    print "\n".join(out)


def handle_db_unrestrict_command(args):
    """Will return a SQL statement to unrestrict the access to the given
    tables by granting all priviledges to the table in the public
    scheme. The restricted view will be dropped."""
    out = []
    out.append("-- Execute this as user postgres")
    out.append("GRANT ALL ON TABLE public.%ss TO PUBLIC;" % args.modul)
    out.append("DROP VIEW IF EXISTS %ss;" % (args.modul))
    print "\n".join(out)
