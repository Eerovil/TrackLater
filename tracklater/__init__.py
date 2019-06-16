from flask import Flask
import os
from tracklater.database import db
from tracklater.settings_utils import settings_wrapper as settings  # noqa

import logging
logger = logging.getLogger(__name__)


def create_app(name=__name__):
    app = Flask(name)

    DIRECTORY = os.path.dirname(os.path.realpath(__file__))

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database.db'.format(DIRECTORY)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    from tracklater.models import ApiCall, Project, Issue, Entry  # noqa

    db.init_app(app)
    with app.app_context():
        db.create_all()

    from tracklater import views

    app.register_blueprint(views.bp)

    return app


def run():
    app = create_app(name="tracklater")
    app.run(debug=True, port=5000, host="localhost")
