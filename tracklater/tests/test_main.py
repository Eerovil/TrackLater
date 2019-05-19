from main import Parser

import pytest

from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def mock_main(monkeypatch):
    monkeypatch.setattr('settings.ENABLED_MODULES', [
        'jira'
    ])


@pytest.fixture()
def parser():
    _parser = Parser(datetime.now() - timedelta(days=7), datetime.now())
    return _parser


def test_parse(parser):
    parser.parse()
