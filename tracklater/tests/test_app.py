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
    from main import store_parser_to_database
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    parser = Parser(start_date, end_date)
    parser.entries = parser.get_entries()
    with app.app_context():
        store_parser_to_database(parser, 'toggl', start_date, end_date)

        db_entries = Entry.query.all()
        assert len(parser.entries) == len(db_entries)


def test_database_projects(client, db: Any):
    from timemodules.toggl import Parser
    from main import store_parser_to_database
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    parser = Parser(start_date, end_date)
    parser.projects = parser.get_projects()
    with app.app_context():
        store_parser_to_database(parser, 'toggl', start_date, end_date)

        db_projects = Project.query.all()
        assert len(parser.projects) == len(db_projects)


def test_database_issues(client, db: Any):
    from timemodules.jira import Parser
    from main import store_parser_to_database
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    parser = Parser(start_date, end_date)
    parser.issues = parser.get_issues()
    with app.app_context():
        store_parser_to_database(parser, 'jira', start_date, end_date)

        db_issues = Issue.query.all()
        assert len(parser.issues) == len(db_issues)


def test_database_jira_caching(client, db: Any):
    from timemodules.jira import Parser
    from main import store_parser_to_database, set_parser_caching_data
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()
    parser = Parser(start_date, end_date)
    parser.issues = parser.get_issues()
    with app.app_context():
        store_parser_to_database(parser, 'jira', start_date, end_date)

    parser = Parser(start_date, end_date)
    # Skip caching first
    parser.issues = parser.get_issues()
    # We get 6 issues again
    assert len(parser.issues) == 6

    parser = Parser(start_date, end_date)
    with app.app_context():
        set_parser_caching_data(parser, 'jira')  # Fetch caching values
    parser.issues = parser.get_issues()
    # Since all 6 are already in database, get_issues should just run once (check jira.py)
    # Hence, wwith testing data we get the 3 last issues as a response
    assert len(parser.issues) == 3

