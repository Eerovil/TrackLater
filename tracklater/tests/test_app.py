import pytest
import os

from app import app

from typing import Any
from datetime import datetime, timedelta

from models import Entry, Issue, Project


@pytest.fixture
def client(db):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database_testing.db'
    client = app.test_client()
    db.init_app(app)
    with app.app_context():
        db.create_all()

    yield client
    os.remove("database_testing.db")


def test_app_root(client):
    response = client.get('/')
    assert response.status_code == 200


def test_app_listmodules(client):
    response = client.get('/listmodules')
    assert response.status_code == 200


def test_app_fetchdata(client):
    response = client.get('/fetchdata')
    assert response.status_code == 200


def test_database_entries(client, db: Any):
    from timemodules.toggl import Parser
    parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    entries = parser.get_entries()
    with app.app_context():
        for entry in entries:
            entry.module = 'toggl'
            db.session.add(entry)
        db.session.commit()

        db_entries = Entry.query.all()
        assert len(entries) == len(db_entries)


def test_database_projects(client, db: Any):
    from timemodules.toggl import Parser
    parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    projects = parser.get_projects()
    with app.app_context():
        for project in projects:
            project.module = 'toggl'
            db.session.add(project)
        db.session.commit()

        db_projects = Project.query.all()
        assert len(projects) == len(db_projects)


def test_database_issues(client, db: Any):
    from timemodules.jira import Parser
    parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    issues = parser.get_issues()
    with app.app_context():
        for issue in issues:
            issue.module = 'jira'
            db.session.add(issue)
        db.session.commit()

        db_issues = Issue.query.all()
        assert len(issues) == len(db_issues)
