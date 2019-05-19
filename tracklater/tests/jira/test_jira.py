from timemodules.jira import Parser

import pytest
import os

from datetime import datetime, timedelta

TEST_URL = 'mock://jira.test'
TEST_KEY = 'TEST'

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(autouse=True)
def mock_jira_settings(monkeypatch):
    monkeypatch.setattr('settings.JIRA', {
        'group1': {
            'CREDENTIALS': ('', ''),
            'URL': 'mock://jira.test',
            'PROJECT_KEY': 'TEST',
        }
    })
    monkeypatch.setattr('timemodules.jira.ISSUES_PER_PAGE', 3)
    monkeypatch.setattr('timemodules.jira.CACHE_LOCATION', DIRECTORY)

    yield
    try:
        os.remove('{}/{}.jira-cache'.format(DIRECTORY, 'group1'))
    except FileNotFoundError:
        pass


@pytest.fixture(autouse=True)
def mock_jira_requests(requests_mock):
    with open(DIRECTORY + '/search_results.json', 'r') as f:
        requests_mock.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary,issuetype'
            '&maxResults=3'.format(
                JIRA_URL=TEST_URL, JIRA_KEY=TEST_KEY
            ),
            text="\n".join(f.readlines())
        )

    with open(DIRECTORY + '/search_results_2.json', 'r') as f:
        requests_mock.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary,issuetype'
            '&maxResults=3&startAt=3'.format(
                JIRA_URL=TEST_URL, JIRA_KEY=TEST_KEY
            ),
            text="\n".join(f.readlines())
        )


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    _parser.credentials = ('', '')
    return _parser


def test_create_parser(parser: Parser):
    assert parser is not None


def test_fetch_issues(parser: Parser):
    data = parser.fetch_issues(TEST_URL, TEST_KEY)
    assert data['issues'][0]['key'] == 'TEST-1'

    data = parser.fetch_issues(TEST_URL, TEST_KEY, start_from=3)
    assert data['issues'][0]['key'] == 'TEST-4'


def test_get_group_issues(parser: Parser):
    import settings
    issues = parser.get_group_issues('group1', settings.JIRA['group1'])
    assert len(issues) == 6


def test_get_issues(parser: Parser):
    issues = parser.get_issues()
    assert len(issues) == 6


def test_cache(parser: Parser):
    parser.get_issues()
    issues = parser.get_issues()
    assert len(issues) == 6
