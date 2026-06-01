import os
from datetime import datetime, timedelta

import pytest

from tracklater import create_app
from tracklater.database import db
from tracklater.models import Entry
from tracklater.timemodules.local import (
    Parser, MODULE_NAME, default_project_pid, resolve_entry_group_project,
)

DIRECTORY = os.path.dirname(os.path.realpath(__file__))
app = create_app()


@pytest.fixture()
def parser():
    return Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())


def test_local_get_projects(parser):
    projects = parser.get_projects()
    assert len(projects) == 3
    pids = {p.pid for p in projects}
    assert 'group1:Development' in pids
    assert 'group1:Bug fixing' in pids
    assert 'group2:Development' in pids


def test_default_project_pid_skips_vikatilanteet():
    assert default_project_pid('group1') == 'group1:Development'


def test_resolve_entry_group_project():
    now = datetime.utcnow()
    entry = Entry(start_time=now, group='storm')
    resolve_entry_group_project(entry)
    assert entry.project is None  # storm not in test LOCAL settings

    entry = Entry(start_time=now, project='group1:Bug fixing')
    resolve_entry_group_project(entry)
    assert entry.group == 'group1'


def test_local_add_modify_delete(parser: Parser):
    parser.entries = []
    entry = Entry(
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow() - timedelta(hours=1),
        title='Local new entry',
        group='group1',
    )
    created = parser.create_entry(entry, None)
    assert created.id
    assert created.project == 'group1:Development'
    assert created.group == 'group1'

    created.title = 'Local modified entry'
    updated = parser.update_entry(created.id, created, None)
    assert updated.title == 'Local modified entry'
    assert updated.id == created.id

    parser.entries = [updated]
    parser.delete_entry(created.id)
    assert len(parser.entries) == 0


def test_local_get_entries_from_database(parser):
    start = datetime.utcnow() - timedelta(days=1)
    end = datetime.utcnow()
    parser.start_date = start
    parser.end_date = end

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database_local_test.db'.format(DIRECTORY)
    with app.app_context():
        db.create_all()
        db.session.add(Entry(
            module=MODULE_NAME,
            id='local-test-1',
            start_time=start + timedelta(hours=1),
            end_time=start + timedelta(hours=2),
            title='Stored entry',
            group='group1',
        ))
        db.session.commit()

        entries = parser.get_entries()
        assert len(entries) == 1
        assert entries[0].title == 'Stored entry'
        assert entries[0].project == 'group1:Development'

        db.session.query(Entry).filter(Entry.module == MODULE_NAME).delete()
        db.session.commit()

    db_path = '{}/database_local_test.db'.format(DIRECTORY)
    if os.path.exists(db_path):
        os.remove(db_path)
