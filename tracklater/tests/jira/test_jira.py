from timemodules.jira import Parser

import pytest
import os

from datetime import datetime, timedelta

TEST_URL = 'mock://jira.test'
TEST_KEY = 'TEST'

DIRECTORY = os.path.dirname(os.path.realpath(__file__))


@pytest.fixture(autouse=True)
def mock_jira_settings(monkeypatch):
    return


@pytest.fixture(autouse=True)
def mock_jira_requests(requests_mock):
    with open(DIRECTORY + '/search_results.json', 'r') as f:
        requests_mock.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary,issuetype'
            '&maxResults=100'.format(
                JIRA_URL=TEST_URL, JIRA_KEY=TEST_KEY
            ),
            text="\n".join(f.readlines())
        )

    with open(DIRECTORY + '/search_results_2.json', 'r') as f:
        requests_mock.get(
            '{JIRA_URL}/rest/api/2/search?jql=project={JIRA_KEY}&fields=key,summary,issuetype'
            '&maxResults=100&startAt=4'.format(
                JIRA_URL=TEST_URL, JIRA_KEY=TEST_KEY
            ),
            text="\n".join(f.readlines())
        )


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    _parser.credentials = ('', '')
    return _parser


def test_create_parser(parser):
    assert parser is not None


def test_fetch_issues(parser):
    data = parser.fetch_issues(TEST_URL, TEST_KEY)
    assert data['issues'][0]['key'] == 'TEST-1'

    data = parser.fetch_issues(TEST_URL, TEST_KEY, start_from=4)
    assert data['issues'][0]['key'] == 'TEST-4'
