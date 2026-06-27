import os
from datetime import datetime, timedelta

import pytest

from tracklater import create_app
from tracklater.models import Entry
from tracklater.ai_local import populate_local_entries

DIRECTORY = os.path.dirname(os.path.realpath(__file__))
app = create_app()


@pytest.fixture
def client(db):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database_ai_test.db'.format(DIRECTORY)
    with app.app_context():
        db.create_all()
    yield app.test_client()
    path = '{}/database_ai_test.db'.format(DIRECTORY)
    if os.path.exists(path):
        os.remove(path)


def test_populate_local_from_git_commit(client, monkeypatch):
    from tracklater import settings as app_settings
    from tracklater.database import db

    monkeypatch.setattr(app_settings, 'ENABLED_MODULES', ['gitmodule', 'toggl'])
    monkeypatch.setattr(app_settings, 'TOGGL', {
        'global': {'API_KEY': 'x'},
        'group1': {
            'NAME': 'First',
            'PROJECTS': {'Development': 'default'},
        },
    })

    start = datetime(2020, 5, 22, 6, 0, 0)
    end = datetime(2020, 5, 22, 20, 0, 0)
    with app.app_context():
        db.session.query(Entry).delete()
        db.session.add(Entry(
            module='gitmodule',
            id='git-pop-1',
            start_time=datetime(2020, 5, 22, 9, 0, 0),
            group='group1',
            text='repo [main] - auto translate updates',
        ))
        db.session.commit()
        created = populate_local_entries(start, end)
    assert len(created) == 1
    assert created[0].project == "group1:Development"
    assert 'auto translate updates' in (created[0].title or '').lower()
    assert (created[0].end_time - created[0].start_time) >= timedelta(minutes=30)
