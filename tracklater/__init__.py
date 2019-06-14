from flask import Flask
import os
from tracklater.database import db

import logging
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    DIRECTORY = os.path.dirname(os.path.realpath(__file__))

    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}/database.db'.format(DIRECTORY)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        db.create_all()

    from tracklater import views

    app.register_blueprint(views.bp)

    app.add_url_rule("/", endpoint="index", view_func=lambda: app.send_static_file('index.html'))

    return app
