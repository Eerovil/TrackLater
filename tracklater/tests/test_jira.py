from tracklater.timemodules.jira import Parser, Provider

import pytest
import os

from datetime import datetime, timedelta

TEST_URL = 'mock://jira.test'
TEST_KEY = 'TEST'

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture()
def parser():
    _parser = Parser(datetime.utcnow() - timedelta(days=7), datetime.utcnow())
    _parser.credentials = ('', '')
    return _parser


@pytest.fixture()
def provider():
    _provider = Provider(('', ''))
    return _provider


def test_create_parser(parser: Parser):
    assert parser is not None


def test_fetch_issues(provider: Provider):
    data = provider.fetch_issues(TEST_URL, TEST_KEY)
    assert data['issues'][0]['key'] == 'TEST-1'

    data = provider.fetch_issues(TEST_URL, TEST_KEY, start_from=3)
    assert data['issues'][0]['key'] == 'TEST-4'


def test_get_group_issues(parser: Parser, provider: Provider):
    from tracklater import settings
    issues = parser.get_group_issues(provider, 'group1', settings.JIRA['group1'])
    assert len(issues) == 6


def test_get_issues(parser: Parser):
    issues = parser.get_issues()
    assert len(issues) == 6


def test_cache(parser: Parser):
    parser.get_issues()
    issues = parser.get_issues()
    assert len(issues) == 6
