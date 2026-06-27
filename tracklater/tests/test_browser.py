"""
Opt-in end-to-end browser test for the lazy Toggl sync UI.

Heavy (boots the Flask app + a real Chromium via Playwright), so it only runs
when RUN_BROWSER_TESTS=1 and Playwright is installed:

    pip install playwright && python -m playwright install chromium
    RUN_BROWSER_TESTS=1 pytest tracklater/tests/test_browser.py

It drives the actual SPA: draft styling, the "Save week (N)" button, the
/saveweek POST, and the draft->synced transition after the worker drains.
"""
import os
import socket
import tempfile
import threading
import time
from datetime import datetime, timedelta

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get('RUN_BROWSER_TESTS'),
    reason="set RUN_BROWSER_TESTS=1 to run browser tests (needs playwright + chromium)",
)


def _free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_save_week_ui_flow(monkeypatch):
    playwright = pytest.importorskip("playwright.sync_api")

    from tracklater import settings as s
    monkeypatch.setattr(s, 'TESTING', True, raising=False)
    monkeypatch.setattr(s, 'ENABLED_MODULES', ['gitmodule', 'toggl'], raising=False)
    monkeypatch.setattr(s, 'TOGGL', {
        'global': {'API_KEY': 'x'},
        'group1': {'NAME': 'First Client', 'PROJECTS': {'Development': 'd'}},
    }, raising=False)
    monkeypatch.setattr(s, 'UI_SETTINGS', {
        'toggl': {'global': '#E01A22'}, 'gitmodule': {'global': '#F44D27'},
    }, raising=False)
    monkeypatch.setattr(s, 'GIT', {'global': {'EMAILS': []}}, raising=False)
    for attr in ('OVERRIDE_START', 'OVERRIDE_END'):
        monkeypatch.delattr(s, attr, raising=False)

    tmp = os.path.join(tempfile.gettempdir(), 'tl_browser_test.db')
    if os.path.exists(tmp):
        os.remove(tmp)
    monkeypatch.setenv('TRACKLATER_DB_URI', 'sqlite:///' + tmp)

    from tracklater import create_app
    from tracklater.database import db
    from tracklater.models import Entry, Project
    from tracklater import sync_worker

    app = create_app()

    now = datetime.utcnow()
    monday = now - timedelta(days=now.weekday())

    def at(hour):
        return monday.replace(hour=hour, minute=0, second=0, microsecond=0)

    with app.app_context():
        db.session.merge(Project(module='toggl', pid='group1:Development',
                                 group='group1', title='First Client - Development'))
        db.session.add(Entry(module='toggl', id='draftA', is_draft=True, toggl_id=None,
                             start_time=at(10), end_time=at(11), title='Draft one',
                             project='group1:Development', group='group1'))
        db.session.add(Entry(module='toggl', id='draftB', is_draft=True, toggl_id=None,
                             start_time=at(12), end_time=at(13), title='Draft two',
                             project='group1:Development', group='group1'))
        db.session.add(Entry(module='toggl', id='999', is_draft=False, toggl_id='999',
                             start_time=at(14), end_time=at(15), title='Synced one',
                             project='group1:Development', group='group1'))
        db.session.commit()

    port = _free_port()
    server = threading.Thread(
        target=lambda: app.run(port=port, use_reloader=False, threaded=True),
        daemon=True,
    )
    server.start()
    time.sleep(2)

    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("dialog", lambda d: d.accept())  # auto-accept the Save confirm()
        page.goto("http://localhost:{}/".format(port), wait_until="networkidle")
        page.wait_for_selector(".vis-item", timeout=15000)
        time.sleep(1.5)

        assert page.locator(".vis-item.draft").count() == 2
        assert page.locator(".vis-item").count() == 3
        save = page.get_by_role("button", name="Save week", exact=False)
        assert save.count() == 1
        assert "2" in save.first.inner_text()
        assert save.first.is_disabled() is False

        save.first.click()
        time.sleep(2)

        with app.app_context():
            from tracklater.models import SyncJob
            jobs = {j.entry_id for j in SyncJob.query.all()}
        assert jobs == {'draftA', 'draftB'}

        # Drain the queue and reload: drafts become synced, Save disables.
        with app.app_context():
            sync_worker.process_pending_jobs()
        page.reload(wait_until="networkidle")
        page.wait_for_selector(".vis-item", timeout=15000)
        time.sleep(1.5)
        assert page.locator(".vis-item.draft").count() == 0
        assert page.get_by_role("button", name="Save week", exact=False).first.is_disabled() is True

        browser.close()

    if os.path.exists(tmp):
        os.remove(tmp)
