from flask import Flask
import os
from tracklater.database import db
from tracklater.settings_utils import settings_wrapper as settings  # noqa

import logging
logger = logging.getLogger(__name__)


def create_app(name=__name__):
    app = Flask(name)

    DIRECTORY = os.path.dirname(os.path.realpath(__file__))

    # TRACKLATER_DB_URI lets the test suite point the app at a throwaway database.
    # This flask_sqlalchemy version binds the engine at db.init_app() time, so a
    # per-test config override comes too late; the env var is read here instead,
    # before init_app, guaranteeing tests never touch the real database.db.
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'TRACKLATER_DB_URI', 'sqlite:///{}/database.db'.format(DIRECTORY))
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from tracklater.models import ApiCall, Project, Issue, Entry, SyncJob  # noqa

    db.init_app(app)
    with app.app_context():
        db.create_all()
        from tracklater.migrations import run_migrations
        run_migrations()

    from tracklater import views

    app.register_blueprint(views.bp)

    from tracklater.sync_worker import start_worker
    start_worker(app)

    return app


def run():
    app = create_app(name="tracklater")
    app.run(debug=True, port=5000, host="localhost")
