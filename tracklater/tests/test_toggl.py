from tracklater.timemodules.toggl import Parser, MODULE_NAME
from tracklater import sync_worker
from tracklater.models import Entry, SyncJob

import pytest
import os

from datetime import datetime, timedelta

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def app_ctx(db):
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database_toggl_test.db'.format(DIRECTORY)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
    path = '{}/database_toggl_test.db'.format(DIRECTORY)
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture()
def parser():
    return Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())


def test_toggl_get_entries(parser, app_ctx):
    data = parser.get_entries()
    assert len(data) == 3
    # Fetched entries are synced, linked to their Toggl id.
    assert all(not e.is_draft for e in data)
    assert all(e.toggl_id == e.id for e in data)


def test_toggl_get_projects(parser):
    # Synthetic group:name projects from settings.TOGGL (group1/group2 × 2 each).
    data = parser.get_projects()
    assert len(data) == 4


def test_create_entry_is_local_draft(parser, app_ctx):
    entry = Entry(
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow() - timedelta(hours=1),
        title="New draft",
        project="group1:Development",
    )
    created = parser.create_entry(entry, None)
    assert created.is_draft is True
    assert created.toggl_id is None
    assert created.id != "group1:Development"  # fresh uuid, not the project
    assert created.group == "group1"


def test_update_preserves_toggl_link_and_flips_to_draft(parser, app_ctx, db):
    db.session.add(Entry(
        module=MODULE_NAME, id="synced-1", toggl_id="999", is_draft=False,
        start_time=datetime.utcnow() - timedelta(hours=3),
        end_time=datetime.utcnow() - timedelta(hours=2),
        title="Synced", project="group1:Development", group="group1",
    ))
    db.session.commit()
    edit = Entry(
        start_time=datetime.utcnow() - timedelta(hours=3),
        end_time=datetime.utcnow() - timedelta(hours=2),
        title="Edited", project="group1:Development",
    )
    updated = parser.update_entry("synced-1", edit, None)
    assert updated.is_draft is True
    assert updated.toggl_id == "999"  # link kept -> worker will UPDATE not CREATE


def test_save_and_sync_create(app_ctx, db):
    """A new draft, once enqueued, is pushed to Toggl and re-keyed to its id."""
    db.session.add(Entry(
        module=MODULE_NAME, id="draft-1", toggl_id=None, is_draft=True,
        start_time=datetime.utcnow() - timedelta(hours=2),
        end_time=datetime.utcnow() - timedelta(hours=1),
        title="To push", project="group1:Development", group="group1",
    ))
    db.session.commit()
    sync_worker.enqueue("draft-1", "create")
    assert SyncJob.query.count() == 1

    processed = sync_worker.process_pending_jobs()
    assert processed == 1
    assert SyncJob.query.count() == 0
    # Original uuid row replaced by one keyed to the new Toggl id, now synced.
    assert Entry.query.filter(Entry.id == "draft-1").first() is None
    synced = Entry.query.filter(Entry.module == MODULE_NAME).first()
    assert synced.is_draft is False
    assert synced.toggl_id == synced.id


def test_enqueue_dedupes_by_entry(app_ctx, db):
    sync_worker.enqueue("e1", "create")
    sync_worker.enqueue("e1", "update", toggl_id="55")
    assert SyncJob.query.count() == 1
    job = SyncJob.query.first()
    assert job.action == "update"
    assert job.toggl_id == "55"


@pytest.fixture()
def client(db):
    import json
    from flask import Flask
    from tracklater import views
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database_toggl_ep.db'.format(DIRECTORY)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    app.register_blueprint(views.bp)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()
    path = '{}/database_toggl_ep.db'.format(DIRECTORY)
    if os.path.exists(path):
        os.remove(path)


def _ms(dt):
    import time
    return int(time.mktime(dt.timetuple()) * 1000)


def test_saveweek_queues_drafts_with_project_only(client, db):
    now = datetime.utcnow()
    db.session.add(Entry(
        module=MODULE_NAME, id="d-proj", is_draft=True, toggl_id=None,
        start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1),
        title="has project", project="group1:Development", group="group1",
    ))
    db.session.add(Entry(
        module=MODULE_NAME, id="d-noproj", is_draft=True, toggl_id=None,
        start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1),
        title="no project", project=None,
    ))
    db.session.commit()

    resp = client.post('/saveweek', json={
        'from': _ms(now - timedelta(days=1)),
        'to': _ms(now + timedelta(days=1)),
    })
    import json
    body = json.loads(resp.data)
    assert body == {"queued": 1, "skipped": 1}
    assert SyncJob.query.count() == 1
    assert SyncJob.query.first().entry_id == "d-proj"


def test_deleteentry_enqueues_remote_delete_when_synced(client, db):
    now = datetime.utcnow()
    db.session.add(Entry(
        module=MODULE_NAME, id="123", is_draft=False, toggl_id="123",
        start_time=now - timedelta(hours=2), end_time=now - timedelta(hours=1),
        title="synced", project="group1:Development", group="group1",
    ))
    db.session.commit()

    resp = client.post('/deleteentry', json={'module': MODULE_NAME, 'entry_id': '123'})
    assert resp.status_code == 200
    assert Entry.query.filter(Entry.id == "123").first() is None
    job = SyncJob.query.filter(SyncJob.entry_id == "123").first()
    assert job is not None and job.action == "delete" and job.toggl_id == "123"
